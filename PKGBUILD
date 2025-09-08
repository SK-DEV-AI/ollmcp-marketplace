# Maintainer: Jules The AI Assistant

pkgname='ollmcp-marketplace-git'
_pkgname='ollmcp-marketplace'
_subpkgname='mcp-client-for-ollama'
pkgver=r18.df36fad # This will be updated by pkgver()
pkgrel=1
pkgdesc="A TUI client for interacting with Ollama models and MCP servers, now with MCP-HUB."
arch=('any')
url="https://github.com/SK-DEV-AI/ollmcp-marketplace"
license=('MIT')
depends=(
    'python'
    'python-typer'
    'python-requests'
    'python-rich'
    'python-prompt_toolkit'
    'python-pygments'
    'python-zeroconf'
    'python-ollama'
    'python-mcp'
)
makedepends=('git' 'python-build' 'python-installer' 'python-wheel')
optdepends=(
    'ollama: for running the required Ollama service'
    'nodejs: for running JavaScript-based MCP servers'
)
source=("git+https://github.com/SK-DEV-AI/ollmcp-marketplace.git")
sha256sums=('SKIP')

# This function automatically generates the version number from the git history.
pkgver() {
  cd "$srcdir/$_pkgname"
  git describe --long --tags 2>/dev/null || printf "r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

# The build function creates a Python wheel.
build() {
  cd "$srcdir/$_pkgname/$_subpkgname"
  python -m build --wheel --no-isolation
}

# The package function installs the built wheel into the package directory.
package() {
  cd "$srcdir/$_pkgname/$_subpkgname"
  python -m installer --destdir="$pkgdir" dist/*.whl
}
