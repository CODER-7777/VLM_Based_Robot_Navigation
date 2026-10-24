package main

import (
	"bytes"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"io"
	"math/big"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

func fixtureTLS(t *testing.T, names []string, expired bool) ([]byte, tls.Certificate) {
	t.Helper()
	key, _ := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	root := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "Synthetic launcher fixture CA"},
		NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour),
		IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign | x509.KeyUsageDigitalSignature}
	rootDER, err := x509.CreateCertificate(rand.Reader, root, root, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	root, _ = x509.ParseCertificate(rootDER)
	leaf := &x509.Certificate{SerialNumber: big.NewInt(2), DNSNames: names,
		NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour),
		KeyUsage: x509.KeyUsageDigitalSignature, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
	if names == nil {
		leaf.IPAddresses = []net.IP{net.ParseIP("127.0.0.1")}
	}
	if expired {
		leaf.NotBefore = time.Now().Add(-48 * time.Hour)
		leaf.NotAfter = time.Now().Add(-24 * time.Hour)
	}
	der, err := x509.CreateCertificate(rand.Reader, leaf, root, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	return pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: rootDER}), tls.Certificate{Certificate: [][]byte{der}, PrivateKey: key}
}

func fixtureBridge(t *testing.T, handler http.Handler, names []string, expired bool) (*Bridge, *httptest.Server) {
	t.Helper()
	ca, cert := fixtureTLS(t, names, expired)
	upstream := httptest.NewUnstartedServer(handler)
	upstream.TLS = &tls.Config{Certificates: []tls.Certificate{cert}, MinVersion: tls.VersionTLS12}
	upstream.Config.ErrorLog = nil
	upstream.StartTLS()
	t.Cleanup(upstream.Close)
	digest := sha256.Sum256(ca)
	b, err := newBridge(upstream.URL, ca, hex.EncodeToString(digest[:]))
	if err != nil {
		t.Fatal(err)
	}
	b.setOrigin(18765)
	t.Cleanup(b.transport.CloseIdleConnections)
	return b, upstream
}

func localRequest(b *Bridge, method, path string, body io.Reader) *http.Request {
	r := httptest.NewRequest(method, b.origin+path, body)
	r.RequestURI = path
	r.URL.Scheme = ""
	r.URL.Host = ""
	r.RemoteAddr = "127.0.0.1:4321"
	r.AddCookie(&http.Cookie{Name: accessCookie, Value: b.secret})
	if method == http.MethodPost {
		r.Header.Set("Origin", b.origin)
	}
	return r
}

func TestReopenKeepsExistingBridgeAndRejectsWrongInstance(t *testing.T) {
	b, _ := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("reopen must not contact the study server")
	}), nil, false)
	listener, err := net.Listen("tcp4", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	b.setOrigin(port)
	server := &http.Server{Handler: b}
	go server.Serve(listener)
	t.Cleanup(func() { server.Close() })
	path := filepath.Join(t.TempDir(), "state", "launcher.json")
	if err := saveInstance(path, b); err != nil {
		t.Fatal(err)
	}
	if runtime.GOOS != "windows" {
		info, _ := os.Stat(path)
		if info.Mode().Perm() != 0600 {
			t.Fatal("bootstrap token file must be private")
		}
	}
	for range 2 {
		address, err := runningInstance(path, b.upstream.String(), port)
		if err != nil || address != b.launchURL() {
			t.Fatalf("cannot reopen running bridge: %v", err)
		}
	}
	if _, err := runningInstance(path, "https://wrong.example", port); err == nil {
		t.Fatal("accepted wrong study")
	}
	state, _ := readInstance(path)
	state.Secret = strings.Repeat("0", 64)
	value, _ := json.Marshal(state)
	if err := os.WriteFile(path, value, 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := runningInstance(path, b.upstream.String(), port); err == nil {
		t.Fatal("accepted wrong token")
	}
	if err := saveInstance(path, b); err != nil {
		t.Fatal(err)
	}
	removeInstance(path, "wrong token")
	if _, err := os.Stat(path); err != nil {
		t.Fatal("removed another instance's state")
	}
	removeInstance(path, b.secret)
	if _, err := runningInstance(path, b.upstream.String(), port); err == nil {
		t.Fatal("accepted missing state")
	}
	if err := saveInstance(path, b); err != nil {
		t.Fatal(err)
	}
	server.Close()
	if _, err := runningInstance(path, b.upstream.String(), port); err == nil {
		t.Fatal("accepted a stopped launcher")
	}
}

func TestStatusDoesNotBypassLocalAuthorization(t *testing.T) {
	b, _ := fixtureBridge(t, http.NotFoundHandler(), nil, false)
	for _, change := range []func(*http.Request){
		func(r *http.Request) { r.Header.Del("Cookie") },
		func(r *http.Request) { r.Header.Set("Sec-Fetch-Site", "cross-site") },
		func(r *http.Request) { r.Header.Set("Origin", "https://other.example") },
		func(r *http.Request) { r.Host = "other.example" },
	} {
		r := localRequest(b, http.MethodGet, "/_study/status", nil)
		change(r)
		w := httptest.NewRecorder()
		b.ServeHTTP(w, r)
		if w.Code != http.StatusForbidden {
			t.Fatal("status bypassed local authorization")
		}
	}
}

func TestFreshLaunchRequiresLoginButRefreshKeepsSession(t *testing.T) {
	b, _ := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/auth/login" {
			http.SetCookie(w, &http.Cookie{Name: "task5_session", Value: "fixture-login", Path: "/", Secure: true, HttpOnly: true})
			w.WriteHeader(http.StatusSeeOther)
			return
		}
		cookie, err := r.Cookie("task5_session")
		if err != nil || cookie.Value != "fixture-login" {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		w.WriteHeader(http.StatusOK)
	}), nil, false)
	request := func(method, path string, expected int) {
		t.Helper()
		w := httptest.NewRecorder()
		b.ServeHTTP(w, localRequest(b, method, path, nil))
		if w.Code != expected {
			t.Fatalf("%s %s: got %d, expected %d", method, path, w.Code, expected)
		}
	}
	for range 2 {
		request("GET", "/_study/open/"+b.secret, http.StatusSeeOther)
		request("GET", "/api/state", http.StatusUnauthorized)
		request("POST", "/auth/login", http.StatusSeeOther)
		request("GET", "/api/state", http.StatusOK)
		request("GET", "/", http.StatusOK)
		request("GET", "/api/state", http.StatusOK)
	}
}

func TestFreshLaunchWaitsForUploadAndCannotRestoreOldLogin(t *testing.T) {
	started, release := make(chan struct{}), make(chan struct{})
	b, _ := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		close(started)
		<-release
		http.SetCookie(w, &http.Cookie{Name: "task5_session", Value: "delayed-old-session", Path: "/", Secure: true})
		w.WriteHeader(http.StatusOK)
	}), nil, false)
	uploadDone := make(chan int, 1)
	go func() {
		w := httptest.NewRecorder()
		b.ServeHTTP(w, localRequest(b, "POST", "/api/upload", strings.NewReader("fixture recording")))
		uploadDone <- w.Code
	}()
	<-started
	reopenDone := make(chan int, 1)
	go func() {
		w := httptest.NewRecorder()
		b.ServeHTTP(w, localRequest(b, "GET", "/_study/open/"+b.secret, nil))
		reopenDone <- w.Code
	}()
	select {
	case <-reopenDone:
		close(release)
		t.Fatal("reopen cleared login while an upload was still in flight")
	case <-time.After(30 * time.Millisecond):
	}
	close(release)
	if code := <-uploadDone; code != http.StatusOK {
		t.Fatalf("upload interrupted: %d", code)
	}
	if code := <-reopenDone; code != http.StatusSeeOther {
		t.Fatalf("reopen failed: %d", code)
	}
	if len(b.jar.Cookies(b.upstream)) != 0 {
		t.Fatal("old upload response restored the previous login")
	}
}

func TestTLSAndLoginTokensStayInsideLauncher(t *testing.T) {
	const token = "synthetic-server-session-secret"
	b, upstream := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.Contains(r.Header.Get("Cookie"), accessCookie) || r.Header.Get("X-Forwarded-For") != "" {
			t.Error("local cookie or spoofed forwarding address reached server")
		}
		if !strings.HasPrefix(r.Host, "127.0.0.1:") {
			t.Error("bad Host")
		}
		if r.URL.Path == "/auth/login" {
			if r.Header.Get("Origin") != "https://"+r.Host {
				t.Error("wrong upstream Origin")
			}
			http.SetCookie(w, &http.Cookie{Name: "task5_session", Value: token, Path: "/", HttpOnly: true, Secure: true, SameSite: http.SameSiteStrictMode})
			w.Header().Set("Strict-Transport-Security", "max-age=31536000")
			http.Redirect(w, r, "/", http.StatusSeeOther)
			return
		}
		cookie, err := r.Cookie("task5_session")
		if err != nil || cookie.Value != token {
			w.WriteHeader(401)
			return
		}
		_, _ = w.Write([]byte("synthetic signed-in dashboard"))
	}), nil, false)
	if b.transport.TLSClientConfig.InsecureSkipVerify || b.transport.Proxy != nil {
		t.Fatal("unsafe transport")
	}
	r := localRequest(b, "POST", "/auth/login", strings.NewReader("username=fixture&password=synthetic"))
	r.Header.Set("X-Forwarded-For", "172.20.1.1")
	w := httptest.NewRecorder()
	b.ServeHTTP(w, r)
	if w.Code != 303 || w.Header().Get("Location") != "/" {
		t.Fatal(w.Code, w.Body.String())
	}
	if w.Header().Get("Set-Cookie") != "" || w.Header().Get("Strict-Transport-Security") != "" || strings.Contains(w.Body.String(), token) {
		t.Fatal("server login secret exposed to browser")
	}
	w = httptest.NewRecorder()
	b.ServeHTTP(w, localRequest(b, "GET", "/", nil))
	if w.Code != 200 || !strings.Contains(w.Body.String(), "signed-in") {
		t.Fatal(w.Code, w.Body.String())
	}
	if b.upstream.String() != upstream.URL {
		t.Fatal("unexpected endpoint")
	}
}

func TestExternalSitesAndDNSRebindingRejected(t *testing.T) {
	hits := 0
	b, _ := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { hits++ }), nil, false)
	for _, change := range []func(*http.Request){
		func(r *http.Request) { r.Header.Del("Cookie") },
		func(r *http.Request) { r.Host = "attacker.example:18765" },
		func(r *http.Request) { r.Header.Set("Origin", "https://attacker.example") },
		func(r *http.Request) { r.Header.Del("Origin") },
		func(r *http.Request) { r.Header.Set("Sec-Fetch-Site", "cross-site") },
		func(r *http.Request) { r.RemoteAddr = "172.20.1.1:4321" },
	} {
		r := localRequest(b, "POST", "/api/upload", strings.NewReader("fixture"))
		change(r)
		w := httptest.NewRecorder()
		b.ServeHTTP(w, r)
		if w.Code != 403 {
			t.Fatal("expected denial", w.Code)
		}
	}
	if hits != 0 {
		t.Fatal("rejected requests reached server")
	}
	r := localRequest(b, "GET", "/_study/open/"+b.secret, nil)
	r.Header.Del("Cookie")
	w := httptest.NewRecorder()
	b.ServeHTTP(w, r)
	if w.Code != 303 || !strings.Contains(w.Header().Get("Set-Cookie"), "HttpOnly; SameSite=Strict") {
		t.Fatal("bootstrap failed", w.Code)
	}
}

func TestWrongExpiredAndDifferentHostnameCertificatesRejected(t *testing.T) {
	for _, fixture := range []struct {
		names   []string
		expired bool
	}{{[]string{"different.example"}, false}, {nil, true}} {
		b, _ := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { t.Error("untrusted connection accepted") }), fixture.names, fixture.expired)
		w := httptest.NewRecorder()
		b.ServeHTTP(w, localRequest(b, "GET", "/login", nil))
		if w.Code != 502 || !strings.Contains(w.Body.String(), "could not be verified") {
			t.Fatal(w.Code, w.Body.String())
		}
	}
	b, _ := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { t.Error("wrong CA accepted") }), nil, false)
	wrongCA, _ := fixtureTLS(t, nil, false)
	digest := sha256.Sum256(wrongCA)
	wrong, err := newBridge(b.upstream.String(), wrongCA, hex.EncodeToString(digest[:]))
	if err != nil {
		t.Fatal(err)
	}
	wrong.setOrigin(18765)
	defer wrong.transport.CloseIdleConnections()
	w := httptest.NewRecorder()
	wrong.ServeHTTP(w, localRequest(wrong, "GET", "/login", nil))
	if w.Code != 502 {
		t.Fatal("wrong CA should fail", w.Code)
	}
	if _, err := newBridge(defaultUpstream, wrongCA, studyCAFileHash); err == nil {
		t.Fatal("tampered embedded CA accepted")
	}
}

func TestBodyLimitsAndExternalRedirects(t *testing.T) {
	b, _ := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { http.Redirect(w, r, "https://attacker.example", 303) }), nil, false)
	r := localRequest(b, "POST", "/api/upload", strings.NewReader("fixture"))
	r.ContentLength = 300*1024*1024 + 1
	w := httptest.NewRecorder()
	b.ServeHTTP(w, r)
	if w.Code != 413 {
		t.Fatal(w.Code)
	}
	r = localRequest(b, "POST", "/api/upload", strings.NewReader("fixture"))
	r.TransferEncoding = []string{"chunked"}
	w = httptest.NewRecorder()
	b.ServeHTTP(w, r)
	if w.Code != 411 {
		t.Fatal(w.Code)
	}
	w = httptest.NewRecorder()
	b.ServeHTTP(w, localRequest(b, "GET", "/login", nil))
	if w.Code != 502 {
		t.Fatal("external redirect accepted", w.Code)
	}
}

func TestUploadStreamsBeforeBrowserHasFinishedSending(t *testing.T) {
	firstReceived := make(chan struct{})
	b, _ := fixtureBridge(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		first := make([]byte, 4096)
		if _, err := io.ReadFull(r.Body, first); err != nil {
			t.Error(err)
			return
		}
		close(firstReceived)
		rest, err := io.ReadAll(r.Body)
		if err != nil || len(rest) != 4096 || !bytes.Equal(first, rest) {
			t.Error("stream changed or truncated")
		}
		_, _ = w.Write([]byte("uploaded"))
	}), nil, false)
	local := httptest.NewServer(b)
	defer local.Close()
	b.setOrigin(local.Listener.Addr().(*net.TCPAddr).Port)
	reader, writer := io.Pipe()
	defer reader.Close()
	defer writer.Close()
	r, _ := http.NewRequest("POST", local.URL+"/api/upload", reader)
	r.Host = strings.TrimPrefix(b.origin, "http://")
	r.Header.Set("Origin", b.origin)
	r.AddCookie(&http.Cookie{Name: accessCookie, Value: b.secret})
	r.ContentLength = 8192
	result := make(chan error, 1)
	go func() {
		response, err := local.Client().Do(r)
		if err == nil {
			defer response.Body.Close()
			if response.StatusCode != 200 {
				err = io.ErrUnexpectedEOF
			}
		}
		result <- err
	}()
	chunk := bytes.Repeat([]byte("x"), 4096)
	if _, err := writer.Write(chunk); err != nil {
		t.Fatal(err)
	}
	select {
	case <-firstReceived:
	case <-time.After(5 * time.Second):
		t.Fatal("upload was buffered rather than streamed")
	}
	if _, err := writer.Write(chunk); err != nil {
		t.Fatal(err)
	}
	_ = writer.Close()
	select {
	case err := <-result:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("upload did not complete")
	}
}
