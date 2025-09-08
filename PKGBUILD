# Maintainer: Jules The AI Assistant

pkgname='mcp-client-for-ollama-git'
_pkgname='mcp-client-for-ollama'
# This version is a placeholder and will be automatically updated by the pkgver() function.
pkgver=0.18.1.r0.gdeadbeef
pkgrel=1
pkgdesc="A TUI client for interacting with Ollama models and MCP servers, now with MCP-HUB."
arch=('any')
url="https://github.com/SK-DEV-AI/ollmcp-marketplace"
license=('MIT')
depends=('python')
makedepends=('git' 'python-build' 'python-installer' 'python-wheel')
optdepends=(
    'ollama: for running the required Ollama service'
    'nodejs: for running JavaScript-based MCP servers'
)
# This package builds from the latest git source.
source=("git+https://github.com/SK-DEV-AI/ollmcp-marketplace.git")
sha256sums=('SKIP')

# This function automatically generates the version number from the git history.
pkgver() {
  cd "$_pkgname"
  git describe --long --tags 2>/dev/null || printf "r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

# The build function creates a Python wheel.
build() {
  cd "$_pkgname"
  python -m build --wheel --no-isolation
}

# The package function installs the built wheel into the package directory.
package() {
  cd "$_pkgname"
  python -m installer --destdir="$pkgdir" dist/*.whl
}
