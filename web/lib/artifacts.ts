export function artifactUrl(path?: string | null): string | null {
  if (!path) {
    return null;
  }

  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  return `/api/artifacts?key=${encodeURIComponent(path.replace(/^\//, ""))}`;
}
