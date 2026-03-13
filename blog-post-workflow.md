# Blog repo setup and publishing workflow

Use this workflow any time you want to set up this Hugo blog on a fresh machine, create a post, rename or delete a post, and publish changes.

## Fresh machine setup

This repo only needs Git, Hugo, and the theme submodule. There is no npm, Python, or database setup required.

### macOS

If `brew` is not installed yet, install Homebrew first from `https://brew.sh/`.

Install Git and Hugo:

```bash
brew install git hugo
```

Clone the repo with its theme submodule:

```bash
git clone --recurse-submodules https://github.com/johnswyou/blog.git
cd blog
```

If you already cloned the repo without submodules, run:

```bash
git submodule update --init --recursive
```

Verify the tools:

```bash
git --version
hugo version
```

Start the local site:

```bash
hugo server -D
```

Then open `http://localhost:1313/`.

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

Then clone the repo with its theme submodule:

```bash
git clone --recurse-submodules https://github.com/johnswyou/blog.git
cd blog
```

If you already cloned the repo without submodules, run:

```bash
git submodule update --init --recursive
```

Verify the tools:

```bash
git --version
hugo version
```

Start the local site:

```bash
hugo server -D
```

Then open `http://localhost:1313/`.

If your Linux distro ships an old Hugo version, install a newer one from the official Hugo release page or use Homebrew on Linux:

```bash
brew install hugo
```

## 1. Create a new post

```bash
hugo new blog/my-post/index.md
```

This creates a new leaf bundle at `content/blog/my-post/index.md`.

## 2. Edit the post

Open `content/blog/my-post/index.md` and use front matter like this:

```toml
+++
title = "My Post"
date = 2026-03-13T00:00:00Z
draft = true
+++
```

Use `draft = true` while writing.

## 3. Preview locally while writing

Run:

```bash
hugo server -D
```

The `-D` flag includes draft posts, so you can preview the post before publishing it.

## 4. Mark the post ready to publish

When the post is ready, change:

```toml
draft = false
```

## 5. Verify it appears without draft mode

Run:

```bash
hugo server
```

This shows what Hugo will publish by default. If the post appears here, it is ready for production.

## 6. Commit only source files

Do not commit `public/`.

Commit source files such as:

- `content/`
- `static/`
- `layouts/`
- `hugo.toml`

Example:

```bash
git add content/blog/my-post
git commit -m "Add blog post: My Post"
git push
```

## 7. Let Cloudflare Pages publish the site

After you push, Cloudflare Pages pulls the repo, runs Hugo, and publishes the generated site.

## Rename an existing post

This repo uses leaf bundles, so the folder name under `content/blog/` becomes the URL slug.

Rename a post like this:

```bash
git mv content/blog/old-slug content/blog/new-slug
```

Then update the front matter title if you want the on-page title to change too.

If you want the old URL to redirect to the new one, add this to the post front matter:

```toml
aliases = ["/blog/old-slug/"]
```

After that, preview with `hugo server`, then commit and push the source changes.

## Delete an existing post

Delete a post like this:

```bash
git rm -r content/blog/my-post
```

Then run `hugo server` to make sure the post no longer appears, commit the deletion, and push. Cloudflare Pages will remove the generated page on the next deploy.

## Common gotchas

- If the post shows up with `hugo server -D` but not with `hugo server`, it is usually still a draft. Check that `draft = false`.
- Be careful with the `date` value and timezone. If the timestamp is not what you expect, the post may not appear when you expect or may sort oddly.
- If Hugo warns about missing layout files for kinds like `home`, `section`, `page`, or `taxonomy`, initialize the theme submodule:

```bash
git submodule update --init --recursive
```

- Do not commit `public/`. Cloudflare Pages generates that output during deployment.
- If your post includes images, keep them in the post's leaf bundle directory and commit those source files, not the generated files under `public/`.

## Rule of thumb

If it is in `content/`, `static/`, `layouts/`, or `hugo.toml`, commit it.

If it is in `public/`, do not commit it.
