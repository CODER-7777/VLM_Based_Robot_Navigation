package main

import (
	"net"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestOpeningReservesLauncherBeforeShutdown(t *testing.T) {
	var life browserLife
	now := time.Now()
	life.ping("tab", true, now.Add(-time.Minute))
	life.ping("tab", false, now.Add(-time.Minute))
	if !life.reserveOpen(now, false) || life.beginShutdown(now) {
		t.Fatal("reopening raced with automatic shutdown")
	}
	if !life.beginShutdown(now.Add(browserStartup + browserGrace + time.Second)) {
		// First expiry observation starts its grace period.
		if !life.beginShutdown(now.Add(browserStartup + 2*browserGrace + 2*time.Second)) {
			t.Fatal("unused launcher never shut down")
		}
	}
	if life.reserveOpen(now, false) || life.expect(now) {
		t.Fatal("a closing launcher accepted a reopen reservation")
	}
}

func TestOpenRetriesStartupAndClosingPortWithoutKillingProcesses(t *testing.T) {
	b, _ := fixtureBridge(t, http.NotFoundHandler(), nil, false)
	listener, err := net.Listen("tcp4", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	b.setOrigin(port)
	server := &http.Server{Handler: b}
	go server.Serve(listener)
	t.Cleanup(func() { server.Close() })
	path := filepath.Join(t.TempDir(), "instance.json")
	saved := make(chan error, 1)
	go func() { time.Sleep(50 * time.Millisecond); saved <- saveInstance(path, b) }()
	opened, address, err := listenOrReuse(port, b.upstream.String(), path, time.Second)
	if err != nil || opened != nil || address != b.launchURL() {
		t.Fatalf("startup race failed: %v", err)
	}
	if err := <-saved; err != nil {
		t.Fatal(err)
	}
	b.life.mu.Lock()
	b.life.opening = time.Time{}
	b.life.empty = time.Now().Add(-time.Minute)
	b.life.mu.Unlock()
	if !b.life.beginShutdown(time.Now()) {
		t.Fatal("fixture did not enter shutdown")
	}
	go func() { time.Sleep(50 * time.Millisecond); server.Close() }()
	opened, address, err = listenOrReuse(port, b.upstream.String(), path, time.Second)
	if err != nil || opened == nil || address != "" {
		t.Fatalf("shutdown race failed: %v", err)
	}
	opened.Close()
}

func TestBrowserLifetimeCloseRefreshOtherTabsAndCrash(t *testing.T) {
	var life browserLife
	now := time.Now()
	life.expect(now)
	if life.expired(now.Add(time.Minute)) {
		t.Fatal("exited before browser could start")
	}
	life.ping("first", true, now)
	life.ping("first", false, now.Add(time.Second))
	if life.expired(now.Add(5 * time.Second)) {
		t.Fatal("no navigation/refresh grace period")
	}
	life.ping("replacement", true, now.Add(6*time.Second))
	if life.expired(now.Add(20 * time.Second)) {
		t.Fatal("refresh killed launcher")
	}
	life.ping("second tab", true, now.Add(21*time.Second))
	life.ping("replacement", false, now.Add(22*time.Second))
	if life.expired(now.Add(40 * time.Second)) {
		t.Fatal("closing one tab killed another")
	}
	life.ping("second tab", false, now.Add(41*time.Second))
	life.ping("second tab", true, now.Add(42*time.Second)) // delayed heartbeat after close
	if !life.expired(now.Add(52 * time.Second)) {
		t.Fatal("did not exit after last tab closed")
	}
	life.expect(now.Add(time.Minute))
	life.ping("crashed", true, now.Add(time.Minute))
	if life.expired(now.Add(time.Minute + browserExpiry + time.Second)) {
		t.Fatal("crash grace missing")
	}
	if !life.expired(now.Add(time.Minute + browserExpiry + browserGrace + 2*time.Second)) {
		t.Fatal("crashed browser kept launcher alive")
	}
}

func TestHTMLInjectionAndHeartbeatAuthorization(t *testing.T) {
	b, _ := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html")
		w.Header().Set("Content-Security-Policy", "script-src 'self'")
		_, _ = w.Write([]byte(`<html><head><title>Admin or collector</title></head><body>Study</body></html>`))
	}), nil, false)
	page := httptest.NewRecorder()
	b.ServeHTTP(page, localRequest(b, "GET", "/admin", nil))
	if !strings.Contains(page.Body.String(), `src="/_study/client.js"></script></head>`) || page.Header().Get("Content-Security-Policy") != "script-src 'self'" {
		t.Fatal("lifecycle missing or security policy modified")
	}
	for _, valid := range []bool{false, true} {
		r := localRequest(b, "POST", "/_study/page", strings.NewReader(`{"id":"12345678-1234-1234-1234-123456789abc","open":true}`))
		if !valid {
			r.Header.Del("Cookie")
		}
		w := httptest.NewRecorder()
		b.ServeHTTP(w, r)
		if !valid && w.Code != http.StatusForbidden {
			t.Fatal("unauthenticated heartbeat accepted")
		}
		if valid && w.Code != http.StatusNoContent {
			t.Fatalf("heartbeat failed: %d", w.Code)
		}
	}
}

func TestPreparingAndSignInErrorPagesTrackOpenBrowser(t *testing.T) {
	for _, status := range []int{http.StatusUnauthorized, http.StatusForbidden, http.StatusServiceUnavailable} {
		b, _ := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			w.Header().Set("Content-Security-Policy", "script-src 'self'")
			w.WriteHeader(status)
			_, _ = w.Write([]byte(`<html><meta http-equiv="refresh" content="4"><body>Preparing your collector</body></html>`))
		}), nil, false)
		page := httptest.NewRecorder()
		b.ServeHTTP(page, localRequest(b, "GET", "/", nil))
		if page.Code != status || !strings.Contains(page.Body.String(), `src="/_study/client.js"`) ||
			page.Header().Get("Content-Security-Policy") != "script-src 'self'" {
			t.Fatalf("HTML error page lost presence tracking or changed status/CSP: %d", status)
		}
	}
}
