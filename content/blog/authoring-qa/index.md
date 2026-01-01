+++
title = "Hugo authoring Q&A: add, remove, rename posts"
date = 2026-01-01T00:00:00Z
draft = true
+++

## Q: Where do Kaslaanka blog posts live

Kaslaanka expects a blog section at `content/blog/`.

## Q: What is the recommended structure for a new post

Use a **leaf bundle** so your post and its images live together:

- `content/blog/my-post/index.md`
- `content/blog/my-post/diagram.svg`

Then reference images with a relative path:

- `![Alt](diagram.svg)`

## Q: What is the simplest structure if I have no local images

Create a single Markdown file:

- `content/blog/my-post.md`

## Q: What front matter should I include

Minimum TOML front matter keys:

- `title`
- `date`
- `draft`

Optional organization:

- `tags = ["x"]`
- `categories = ["y"]`

## Q: How do I enable math rendering on a post

- If your site config has `params.math = true` in `hugo.toml`, KaTeX loads site-wide.
- If you disable site-wide math later, enable it per-post by adding `math = true` to the post front matter.

## Q: Is there a convenient command to create a new post

Yes:

```bash
hugo new blog/my-post/index.md
# or
hugo new blog/my-post.md
```

## Q: How do I remove an existing post

Hard remove:

- Leaf bundle: delete `content/blog/my-post/`
- Single file: delete `content/blog/my-post.md`

Soft remove (keep the file, hide the post):

- Set `draft = true` in the post front matter
- It won’t show up unless you build with drafts enabled (e.g. `hugo server -D`)

Deployment note:

- Make sure your deploy step **cleans old output** so deleted posts don’t linger as stale HTML.

## Q: What happens if I rename a leaf bundle directory

Renaming a directory like:

- `content/blog/demo/` to `content/blog/demo_alt/`

will typically change the URL from:

- `/blog/demo/` to `/blog/demo_alt/`

unless you override it with front matter such as `slug` or `url` or custom permalinks.

## Q: What can renaming break

- Inbound links and bookmarks to the old URL
- Internal links that point to the old path, including `ref` and `relref` usage

## Q: What usually does not break when renaming

- Page-bundle images referenced relatively like `![Alt](local-image.svg)`
- Static assets referenced with absolute paths like `![Alt](/images/something.svg)`

## Q: How do I keep the old URL working after a rename

Add an alias in the post front matter:

- `aliases = ["/blog/demo/"]`

This will generate a page at the old location that redirects to the new one. Also ensure your deploy cleans old output so you don’t accidentally serve stale files.
