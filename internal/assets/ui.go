package assets

import (
	"embed"
	"io/fs"
	"net/http"
	"path"
	"strings"
)

//go:embed all:dist
var distFS embed.FS

// GetUIHandler returns an http.Handler that serves the embedded Web UI with SPA/HTML routing.
func GetUIHandler() http.Handler {
	sub, err := fs.Sub(distFS, "dist")
	if err != nil {
		panic("failed to create sub filesystem from embedded dist: " + err.Error())
	}

	fileServer := http.FileServer(http.FS(sub))

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		reqPath := strings.TrimPrefix(path.Clean(r.URL.Path), "/")
		if reqPath == "" || reqPath == "." {
			reqPath = "index.html"
		}

		// 1. Direct file match
		if f, err := sub.Open(reqPath); err == nil {
			_ = f.Close()
			fileServer.ServeHTTP(w, r)
			return
		}

		// 2. Next.js route mapping: e.g. /vehicles -> vehicles.html
		htmlPath := reqPath + ".html"
		if f, err := sub.Open(htmlPath); err == nil {
			_ = f.Close()
			r.URL.Path = "/" + htmlPath
			fileServer.ServeHTTP(w, r)
			return
		}

		// 3. Fallback to index.html for client-side routing
		if f, err := sub.Open("index.html"); err == nil {
			_ = f.Close()
			r.URL.Path = "/index.html"
			fileServer.ServeHTTP(w, r)
			return
		}

		// 4. Final fallback 404
		http.NotFound(w, r)
	})
}
