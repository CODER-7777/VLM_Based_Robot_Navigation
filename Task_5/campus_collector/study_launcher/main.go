// Study Launcher keeps private-CA trust inside this application.
// It never modifies browser/OS trust stores or disables TLS verification.
package main

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"crypto/tls"
	"crypto/x509"
	_ "embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/http/cookiejar"
	"net/http/httputil"
	"net/url"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

// The owner build script supplies only the public study CA here.
//
//go:embed rootCA.crt
var studyCA []byte

const studyCAFileHash = "5d5d81ac9d7a884bf579c3cf9cc478e5b66a907b26a3356b88d4f66baf27b445"
const defaultUpstream = "https://172.26.186.222:8443"
const localName = "iitk-study.localhost"
const accessCookie = "study_launcher_access"

type Bridge struct {
	life      browserLife
	upstream  *url.URL
	origin    string
	secret    string
	jar       http.CookieJar
	transport *http.Transport
	proxy     *httputil.ReverseProxy
	slots     chan struct{}
	uploads   chan struct{}
	// Session changes wait for in-flight proxy responses, including uploads.
	// This prevents a delayed response from restoring a previous login cookie.
	auth sync.RWMutex
}

func newBridge(upstream string, ca []byte, expectedHash string) (*Bridge, error) {
	digest := sha256.Sum256(ca)
	if hex.EncodeToString(digest[:]) != expectedHash {
		return nil, errors.New("the packaged study certificate checksum does not match")
	}
	u, err := url.Parse(upstream)
	if err != nil || u.Scheme != "https" || u.Hostname() == "" || u.User != nil || u.Path != "" || u.RawQuery != "" || u.Fragment != "" {
		return nil, errors.New("the study server must be an HTTPS origin without a path or credentials")
	}
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(ca) {
		return nil, errors.New("the study certificate could not be loaded")
	}
	jar, _ := cookiejar.New(nil)
	secret := make([]byte, 32)
	if _, err = rand.Read(secret); err != nil {
		return nil, err
	}
	b := &Bridge{upstream: u, secret: hex.EncodeToString(secret), jar: jar,
		slots: make(chan struct{}, 32), uploads: make(chan struct{}, 2),
		transport: &http.Transport{
			Proxy:               nil, // Connect directly to the private campus server.
			TLSClientConfig:     &tls.Config{RootCAs: roots, MinVersion: tls.VersionTLS12},
			DialContext:         (&net.Dialer{Timeout: 12 * time.Second, KeepAlive: 30 * time.Second}).DialContext,
			TLSHandshakeTimeout: 12 * time.Second, ResponseHeaderTimeout: 610 * time.Second,
			MaxIdleConnsPerHost: 16, IdleConnTimeout: 30 * time.Second,
		},
	}
	b.proxy = &httputil.ReverseProxy{
		Transport: b.transport,
		Rewrite: func(p *httputil.ProxyRequest) {
			p.SetURL(b.upstream)
			p.Out.Host = b.upstream.Host
			p.Out.Header.Set("Accept-Encoding", "identity")
			for _, name := range []string{"Cookie", "Forwarded", "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto", "X-Real-IP", "Referer", "Origin"} {
				p.Out.Header.Del(name)
			}
			if p.In.Method == http.MethodPost {
				p.Out.Header.Set("Origin", b.upstream.String())
			}
			for _, c := range b.jar.Cookies(b.upstream) {
				p.Out.AddCookie(c)
			}
		},
		ModifyResponse: func(r *http.Response) error {
			// Real server login tokens stay in launcher memory, not browser cookies.
			b.jar.SetCookies(b.upstream, r.Cookies())
			r.Header.Del("Set-Cookie")
			r.Header.Del("Strict-Transport-Security")
			r.Header.Set("Cache-Control", "no-store")
			r.Header.Set("Cross-Origin-Resource-Policy", "same-origin")
			if target := r.Header.Get("Location"); target != "" {
				u, err := url.Parse(target)
				if err != nil || strings.HasPrefix(target, "//") {
					return errors.New("invalid server redirect")
				}
				if u.IsAbs() {
					if u.Scheme != b.upstream.Scheme || u.Host != b.upstream.Host {
						return errors.New("unexpected external server redirect")
					}
					r.Header.Set("Location", u.RequestURI())
				}
			}
			return injectBrowserClient(r)
		},
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			message := "Cannot reach the study server. Check the approved IITK connection and keep this launcher open."
			var verification *tls.CertificateVerificationError
			if errors.As(err, &verification) {
				message = "The study server certificate could not be verified. Contact the study owner; verification has not been bypassed."
			}
			jsonError(w, http.StatusBadGateway, message)
		},
		ErrorLog: log.New(io.Discard, "", 0),
	}
	return b, nil
}

func jsonError(w http.ResponseWriter, code int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": message})
}

func (b *Bridge) setOrigin(port int) {
	b.origin = "http://" + net.JoinHostPort(localName, strconv.Itoa(port))
}

func (b *Bridge) launchURL() string { return b.origin + "/_study/open/" + b.secret }

func (b *Bridge) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	peer, _, err := net.SplitHostPort(r.RemoteAddr)
	address := net.ParseIP(peer)
	if err != nil || address == nil || !address.IsLoopback() {
		jsonError(w, http.StatusForbidden, "This launcher accepts connections only from this computer.")
		return
	}
	if "http://"+r.Host != b.origin || r.URL.IsAbs() || strings.HasPrefix(r.RequestURI, "//") {
		jsonError(w, http.StatusForbidden, "Use the browser address opened by Study Launcher.")
		return
	}
	w.Header().Set("X-Frame-Options", "DENY")
	w.Header().Set("Referrer-Policy", "same-origin")
	if r.Method != http.MethodGet && r.Method != http.MethodPost {
		jsonError(w, http.StatusMethodNotAllowed, "Only GET and POST are supported.")
		return
	}
	if r.Method == http.MethodGet && r.URL.Path == "/_study/open/"+b.secret {
		if !b.life.expect(time.Now()) {
			jsonError(w, http.StatusServiceUnavailable, "The launcher is finishing shutdown. OpenDashboard will start a new instance.")
			return
		}
		// Every explicit launch starts at sign-in. Ordinary page loads keep
		// using this session; saved study data is never changed here.
		b.auth.Lock()
		b.jar, _ = cookiejar.New(nil)
		b.auth.Unlock()
		w.Header().Set("Referrer-Policy", "no-referrer")
		http.SetCookie(w, &http.Cookie{Name: accessCookie, Value: b.secret, Path: "/", HttpOnly: true, SameSite: http.SameSiteStrictMode})
		w.Header().Set("Cache-Control", "no-store")
		http.Redirect(w, r, "/login", http.StatusSeeOther)
		return
	}
	c, err := r.Cookie(accessCookie)
	if err != nil || subtle.ConstantTimeCompare([]byte(c.Value), []byte(b.secret)) != 1 {
		jsonError(w, http.StatusForbidden, "Open the link printed by Study Launcher to access your local dashboard.")
		return
	}
	if r.Header.Get("Sec-Fetch-Site") == "cross-site" || (r.Header.Get("Origin") != "" && r.Header.Get("Origin") != b.origin) {
		jsonError(w, http.StatusForbidden, "Requests from other websites are not accepted.")
		return
	}
	if r.Method == http.MethodPost && r.Header.Get("Origin") != b.origin {
		jsonError(w, http.StatusForbidden, "Use the dashboard opened on this computer.")
		return
	}
	if r.Method == http.MethodGet && r.URL.Path == "/_study/status" {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-store")
		_ = json.NewEncoder(w).Encode(map[string]string{"launcher": "iitk-study-launcher-v1", "upstream": b.upstream.String()})
		return
	}
	if b.lifecycleRequest(w, r) {
		return
	}
	if strings.HasPrefix(r.URL.Path, "/_study/") {
		jsonError(w, http.StatusNotFound, "Launcher route not found.")
		return
	}
	if len(r.TransferEncoding) > 0 || r.ContentLength < 0 {
		jsonError(w, http.StatusLengthRequired, "An explicit upload size is required.")
		return
	}
	limit := int64(65536)
	if r.URL.Path == "/api/upload" {
		limit = 300 * 1024 * 1024
	}
	if r.ContentLength > limit {
		jsonError(w, http.StatusRequestEntityTooLarge, "This recording exceeds the study upload limit.")
		return
	}
	select {
	case b.slots <- struct{}{}:
		defer func() { <-b.slots }()
	default:
		jsonError(w, http.StatusServiceUnavailable, "The launcher is busy; wait for current requests to finish.")
		return
	}
	if r.URL.Path == "/api/upload" {
		select {
		case b.uploads <- struct{}{}:
			defer func() { <-b.uploads }()
		default:
			jsonError(w, http.StatusServiceUnavailable, "Two uploads are already running. Keep the source recording and retry shortly.")
			return
		}
	}
	if r.Method == http.MethodPost && (r.URL.Path == "/auth/login" || r.URL.Path == "/auth/logout") {
		b.auth.Lock()
		defer b.auth.Unlock()
	} else {
		b.auth.RLock()
		defer b.auth.RUnlock()
	}
	r.Body = http.MaxBytesReader(w, r.Body, limit)
	b.proxy.ServeHTTP(w, r)
}

func openBrowser(address string) error {
	var command *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		command = exec.Command("rundll32", "url.dll,FileProtocolHandler", address)
	case "darwin":
		// Prefer a supported recording browser when it is installed in the
		// usual system or per-user Applications folder.
		bases := []string{"/Applications"}
		if home, err := os.UserHomeDir(); err == nil {
			bases = append(bases, filepath.Join(home, "Applications"))
		}
		for _, app := range []string{"Google Chrome.app", "Microsoft Edge.app"} {
			for _, base := range bases {
				path := filepath.Join(base, app)
				if info, err := os.Stat(path); err == nil && info.IsDir() {
					return exec.Command("/usr/bin/open", "-a", path, address).Start()
				}
			}
		}
		command = exec.Command("open", address)
	default:
		command = exec.Command("xdg-open", address)
	}
	return command.Start()
}

// Only the local bootstrap token is cached, never a password or server cookie.
// A second launch verifies the running bridge before reusing its browser link.
type localInstance struct {
	Origin   string `json:"origin"`
	Upstream string `json:"upstream"`
	Secret   string `json:"secret"`
}

func instancePath(port int) string {
	if port <= 0 {
		return ""
	}
	directory, err := os.UserCacheDir()
	if err != nil {
		return ""
	}
	return filepath.Join(directory, "IITK-Study-Launcher", strconv.Itoa(port)+".json")
}

func saveInstance(path string, b *Bridge) error {
	if path == "" {
		return nil
	}
	directory := filepath.Dir(path)
	if err := os.MkdirAll(directory, 0700); err != nil {
		return err
	}
	if err := os.Chmod(directory, 0700); err != nil {
		return err
	}
	f, err := os.CreateTemp(directory, ".instance-")
	if err != nil {
		return err
	}
	defer os.Remove(f.Name())
	err = json.NewEncoder(f).Encode(localInstance{b.origin, b.upstream.String(), b.secret})
	closeErr := f.Close()
	if err != nil {
		return err
	}
	if closeErr != nil {
		return closeErr
	}
	// Windows Rename does not replace an existing destination.
	if runtime.GOOS == "windows" {
		_ = os.Remove(path)
	}
	return os.Rename(f.Name(), path)
}

func readInstance(path string) (localInstance, error) {
	var state localInstance
	info, err := os.Lstat(path)
	if err != nil {
		return state, err
	}
	if !info.Mode().IsRegular() || info.Size() > 4096 || (runtime.GOOS != "windows" && info.Mode().Perm()&0077 != 0) {
		return state, errors.New("unsafe launcher state file")
	}
	f, err := os.Open(path)
	if err != nil {
		return state, err
	}
	defer f.Close()
	err = json.NewDecoder(io.LimitReader(f, 4096)).Decode(&state)
	return state, err
}

func runningInstance(path, upstream string, port int) (string, error) {
	state, err := readInstance(path)
	if err != nil {
		return "", err
	}
	expected := "http://" + net.JoinHostPort(localName, strconv.Itoa(port))
	secret, err := hex.DecodeString(state.Secret)
	if err != nil || len(secret) != 32 || state.Origin != expected || state.Upstream != upstream {
		return "", errors.New("launcher instance does not match this study")
	}
	// Dial loopback directly; never use system proxies or follow redirects.
	transport := &http.Transport{Proxy: nil}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 2 * time.Second,
		CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	r, _ := http.NewRequest(http.MethodPost, "http://"+net.JoinHostPort("127.0.0.1", strconv.Itoa(port))+"/_study/reopen", nil)
	r.Host = net.JoinHostPort(localName, strconv.Itoa(port))
	r.Header.Set("Origin", state.Origin)
	r.AddCookie(&http.Cookie{Name: accessCookie, Value: state.Secret})
	response, err := client.Do(r)
	if err != nil {
		return "", err
	}
	// Older verified releases can still be opened while upgrading, without
	// terminating their process or interrupting their browser's uploads.
	if response.StatusCode == http.StatusNotFound {
		_ = response.Body.Close()
		r.Method = http.MethodGet
		r.URL.Path = "/_study/status"
		response, err = client.Do(r)
		if err != nil {
			return "", err
		}
	}
	defer response.Body.Close()
	var status map[string]string
	if response.StatusCode != http.StatusOK || json.NewDecoder(io.LimitReader(response.Body, 4096)).Decode(&status) != nil || status["launcher"] != "iitk-study-launcher-v1" || status["upstream"] != upstream {
		return "", errors.New("port is not the expected running launcher")
	}
	return state.Origin + "/_study/open/" + state.Secret, nil
}

func removeInstance(path, secret string) {
	if state, err := readInstance(path); err == nil && state.Secret == secret {
		_ = os.Remove(path)
	}
}

// Wait through startup/state-file and shutdown/port-release races. Never move
// to a different port: browser recovery data belongs to this stable origin.
func listenOrReuse(port int, upstream, statePath string, wait time.Duration) (net.Listener, string, error) {
	deadline := time.Now().Add(wait)
	for {
		listener, err := net.Listen("tcp4", net.JoinHostPort("127.0.0.1", strconv.Itoa(port)))
		if err == nil {
			return listener, "", nil
		}
		if !errors.Is(err, syscall.EADDRINUSE) {
			return nil, "", err
		}
		if address, existingErr := runningInstance(statePath, upstream, port); existingErr == nil {
			return nil, address, nil
		}
		if !time.Now().Before(deadline) {
			return nil, "", fmt.Errorf("local port %d is occupied by an application that could not be verified as this study launcher", port)
		}
		time.Sleep(150 * time.Millisecond)
	}
}

func main() {
	upstream := flag.String("origin", defaultUpstream, "Owner-configured HTTPS study server")
	port := flag.Int("port", 18765, "Local launcher port; keep stable for browser upload recovery")
	noOpen := flag.Bool("no-open", false, "Print the browser link without opening it")
	flag.Parse()
	bridge, err := newBridge(*upstream, studyCA, studyCAFileHash)
	if err != nil {
		fmt.Fprintln(os.Stderr, "Study Launcher:", err)
		os.Exit(1)
	}
	listener, existingAddress, err := listenOrReuse(*port, bridge.upstream.String(), instancePath(*port), 12*time.Second)
	if err != nil {
		fmt.Fprintln(os.Stderr, "Study Launcher:", err, "Your saved progress has not been changed.")
		os.Exit(1)
	}
	if existingAddress != "" {
		fmt.Println("Reopening the running launcher. Existing uploads are continuing.")
		if !*noOpen {
			if browserErr := openBrowser(existingAddress); browserErr == nil {
				return
			}
		}
		fmt.Println("Browser link:", existingAddress)
		return
	}
	bridge.setOrigin(listener.Addr().(*net.TCPAddr).Port)
	bridge.life.expect(time.Now())
	statePath := instancePath(*port)
	if err := saveInstance(statePath, bridge); err != nil {
		fmt.Println("Automatic reopen is unavailable; keep the browser link below for this session.")
	}
	defer removeInstance(statePath, bridge.secret)
	server := &http.Server{Handler: bridge, ReadHeaderTimeout: 10 * time.Second, IdleTimeout: 30 * time.Second,
		MaxHeaderBytes: 32768, ErrorLog: log.New(io.Discard, "", 0)}
	watchContext, stopWatching := context.WithCancel(context.Background())
	defer stopWatching()
	go bridge.watchBrowser(watchContext, server)
	fmt.Println("IITK Study Launcher")
	fmt.Println("Close all dashboard tabs when finished; this launcher then exits automatically.")
	fmt.Println("No certificate is installed into this computer's trust stores.")
	fmt.Println("Browser link:", bridge.launchURL())
	if !*noOpen {
		if err = openBrowser(bridge.launchURL()); err != nil {
			fmt.Println("Open the browser link above manually in Chrome or Edge.")
		}
	}
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt)
	go func() {
		<-stop
		fmt.Println("Closing launcher. Keep any browser recovery clips until they are uploaded.")
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = server.Shutdown(ctx)
	}()
	if err = server.Serve(listener); err != nil && err != http.ErrServerClosed {
		fmt.Fprintln(os.Stderr, "Launcher stopped:", err)
		os.Exit(1)
	}
	bridge.transport.CloseIdleConnections()
}
