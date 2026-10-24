package main

import (
	"bytes"
	"context"
	_ "embed"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"
)

//go:embed browser-client.js
var browserClient []byte

const browserGrace = 10 * time.Second
const browserExpiry = 3 * time.Minute
const browserStartup = 2 * time.Minute

type browserLife struct {
	mu       sync.Mutex
	tabs     map[string]time.Time
	closed   map[string]time.Time
	opening  time.Time
	empty    time.Time
	stopping bool
}

func (l *browserLife) expect(now time.Time) bool {
	return l.reserveOpen(now, true)
}

func (l *browserLife) reserveOpen(now time.Time, fresh bool) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.stopping {
		return false
	}
	l.opening = now.Add(browserStartup)
	l.empty = time.Time{}
	// An explicit fresh-login launch replaces stale leases left by a crash.
	// Any other live page registers again on its next heartbeat.
	if fresh {
		l.tabs = make(map[string]time.Time)
	}
	return true
}

func (l *browserLife) ping(id string, open bool, now time.Time) {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.tabs == nil {
		l.tabs = make(map[string]time.Time)
	}
	if open {
		if !l.closed[id].IsZero() {
			return
		}
		if len(l.tabs) < 128 || !l.tabs[id].IsZero() {
			l.tabs[id] = now
		}
		l.opening = time.Time{}
		l.empty = time.Time{}
	} else {
		if l.closed == nil {
			l.closed = make(map[string]time.Time)
		}
		l.closed[id] = now
		delete(l.tabs, id)
		if len(l.tabs) == 0 && l.empty.IsZero() {
			l.empty = now
		}
	}
}

func (l *browserLife) streamOpened(id string, now time.Time) {
	l.mu.Lock()
	delete(l.closed, id)
	l.mu.Unlock()
	l.ping(id, true, now)
}

func (l *browserLife) expired(now time.Time) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.expiredLocked(now)
}

func (l *browserLife) beginShutdown(now time.Time) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.stopping || !l.expiredLocked(now) {
		return false
	}
	l.stopping = true
	return true
}

func (l *browserLife) expiredLocked(now time.Time) bool {
	for id, last := range l.tabs {
		if now.Sub(last) > browserExpiry {
			delete(l.tabs, id)
		}
	}
	for id, closed := range l.closed {
		if now.Sub(closed) > 2*browserExpiry {
			delete(l.closed, id)
		}
	}
	if len(l.tabs) > 0 || now.Before(l.opening) {
		return false
	}
	if l.empty.IsZero() {
		l.empty = now
	}
	return now.Sub(l.empty) >= browserGrace
}

func (b *Bridge) lifecycleRequest(w http.ResponseWriter, r *http.Request) bool {
	if r.Method == http.MethodPost && r.URL.Path == "/_study/reopen" {
		if !b.life.reserveOpen(time.Now(), false) {
			jsonError(w, http.StatusServiceUnavailable, "The launcher is finishing shutdown; opening will retry automatically.")
			return true
		}
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-store")
		_ = json.NewEncoder(w).Encode(map[string]string{"launcher": "iitk-study-launcher-v1", "upstream": b.upstream.String()})
		return true
	}
	if r.Method == http.MethodGet && strings.HasPrefix(r.URL.Path, "/_study/presence/") {
		id := strings.TrimPrefix(r.URL.Path, "/_study/presence/")
		if !validPageID(id) {
			jsonError(w, http.StatusBadRequest, "Invalid browser page.")
			return true
		}
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-store")
		b.life.streamOpened(id, time.Now())
		defer func() { b.life.ping(id, false, time.Now()) }()
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		for {
			control := http.NewResponseController(w)
			_ = control.SetWriteDeadline(time.Now().Add(5 * time.Second))
			if _, err := io.WriteString(w, ": dashboard open\n\n"); err != nil {
				return true
			}
			if control.Flush() != nil {
				return true
			}
			b.life.ping(id, true, time.Now())
			select {
			case <-r.Context().Done():
				return true
			case <-ticker.C:
			}
		}
	}
	if r.Method == http.MethodGet && r.URL.Path == "/_study/client.js" {
		w.Header().Set("Content-Type", "application/javascript; charset=utf-8")
		w.Header().Set("Cache-Control", "no-store")
		_, _ = w.Write(browserClient)
		return true
	}
	if r.Method != http.MethodPost || r.URL.Path != "/_study/page" {
		return false
	}
	var page struct {
		ID   string `json:"id"`
		Open bool   `json:"open"`
	}
	if json.NewDecoder(http.MaxBytesReader(w, r.Body, 1024)).Decode(&page) != nil || !validPageID(page.ID) {
		jsonError(w, http.StatusBadRequest, "Invalid browser heartbeat.")
		return true
	}
	b.life.ping(page.ID, page.Open, time.Now())
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(http.StatusNoContent)
	return true
}

func validPageID(id string) bool { return len(id) == 36 && strings.Trim(id, "abcdef0123456789-") == "" }

func injectBrowserClient(r *http.Response) error {
	if r.StatusCode != http.StatusOK || !strings.HasPrefix(strings.ToLower(r.Header.Get("Content-Type")), "text/html") {
		return nil
	}
	if coding := r.Header.Get("Content-Encoding"); coding != "" && coding != "identity" {
		return errors.New("unexpected compressed dashboard page")
	}
	body, err := io.ReadAll(io.LimitReader(r.Body, 8*1024*1024+1))
	_ = r.Body.Close()
	if err != nil {
		return err
	}
	if len(body) > 8*1024*1024 {
		return errors.New("dashboard page exceeds launcher limit")
	}
	script := []byte(`<script src="/_study/client.js"></script>`)
	lower := bytes.ToLower(body)
	// Insert before application scripts so recording chunks can be checkpointed.
	if offset := bytes.Index(lower, []byte("</head>")); offset >= 0 {
		body = append(append(append([]byte{}, body[:offset]...), script...), body[offset:]...)
	} else if offset := bytes.Index(lower, []byte("<script")); offset >= 0 {
		body = append(append(append([]byte{}, body[:offset]...), script...), body[offset:]...)
	} else {
		body = append(body, script...)
	}
	r.Body = io.NopCloser(bytes.NewReader(body))
	r.ContentLength = int64(len(body))
	r.Header.Set("Content-Length", strconv.Itoa(len(body)))
	r.Header.Del("ETag")
	return nil
}

func (b *Bridge) watchBrowser(ctx context.Context, server *http.Server) {
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case now := <-ticker.C:
			if len(b.slots) > 0 || !b.life.beginShutdown(now) {
				continue
			}
			shutdown, cancel := context.WithTimeout(ctx, 10*time.Second)
			_ = server.Shutdown(shutdown)
			cancel()
			return
		}
	}
}
