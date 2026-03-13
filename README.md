# John You's Blog

This repository contains the source for `https://www.jy-blog.com/`, built with Hugo and deployed with Cloudflare Pages.

The theme is included as a Git submodule at `themes/kaslaanka`.

## Quick start

### macOS

Install Git and Hugo:

```bash
brew install git hugo
```

Clone the repo with its submodules and start the local server:

```bash
git clone --recurse-submodules https://github.com/johnswyou/blog.git
cd blog
hugo server -D
```

### Linux

Install Git and Hugo with your distro package manager.

Debian or Ubuntu:

```bash
sudo apt update
sudo apt install -y git hugo
```

Fedora:

```bash
sudo dnf install git hugo
```

Arch Linux:

```bash
sudo pacman -S git hugo
```

Then clone the repo with its submodules and start the local server:

```bash
git clone --recurse-submodules https://github.com/johnswyou/blog.git
cd blog
hugo server -D
```

If you already cloned the repo without submodules, run:

```bash
git submodule update --init --recursive
```

## Writing and publishing posts

Create a new post:

```bash
hugo new blog/my-post/index.md
```

While writing, preview drafts locally:

```bash
hugo server -D
```

When ready to publish, set `draft = false` in the post front matter, then verify it still appears with:

```bash
hugo server
```

Commit source files such as `content/`, `static/`, `layouts/`, and `hugo.toml`, then push. Cloudflare Pages will build and publish the site.

Do not commit `public/`.

## Full workflow guide

For full instructions, including fresh-machine setup, renaming or deleting posts, and common gotchas, see [`blog-post-workflow.md`](./blog-post-workflow.md).
