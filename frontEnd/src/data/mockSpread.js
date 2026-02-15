/**
 * Mock spread data for the corkboard investigation view.
 *
 * Contract shape (same structure the backend /spread endpoint will return):
 *
 *   source  – the identified origin of the image
 *   nodes   – places where the image was found (most relevant, not exhaustive)
 *   edges   – directed connections showing how the image propagated
 *   summary – high-level stats
 *
 * Every node has:
 *   id       – unique string
 *   label    – short human-readable name
 *   platform – lowercase platform key (reddit, twitter, facebook, news, instagram, tiktok, 4chan, imgur, etc.)
 *   date     – ISO date string (YYYY-MM-DD)
 *   url      – link to the post/page (nullable)
 *
 * The source node is just a regular node referenced by `source.id`.
 * The uploaded image is NOT part of this data — the component receives it separately.
 */

// ---------- small scenario (3 nodes) ----------
export const MOCK_SPREAD_SMALL = {
  source: {
    id: "src",
    label: "Anonymous post",
    platform: "4chan",
    date: "2025-11-28",
    url: null,
  },
  nodes: [
    {
      id: "n1",
      label: "u/truthseeker post",
      platform: "reddit",
      date: "2025-12-01",
      url: "https://reddit.com/r/pics/comments/example",
    },
    {
      id: "n2",
      label: "@breakingnow share",
      platform: "twitter",
      date: "2025-12-02",
      url: "https://twitter.com/breakingnow/status/example",
    },
  ],
  edges: [
    { from: "src", to: "n1" },
    { from: "n1", to: "n2" },
  ],
  summary: {
    total_matches: 2,
    platforms: ["reddit", "twitter"],
  },
};

// ---------- medium scenario (7 nodes) — default demo ----------
export const MOCK_SPREAD_MEDIUM = {
  source: {
    id: "src",
    label: "Anonymous post",
    platform: "4chan",
    date: "2025-11-28",
    url: null,
  },
  nodes: [
    {
      id: "n1",
      label: "u/deepfake_watch post",
      platform: "reddit",
      date: "2025-12-01",
      url: "https://reddit.com/r/pics/comments/example1",
    },
    {
      id: "n2",
      label: "@newsbot retweet",
      platform: "twitter",
      date: "2025-12-02",
      url: "https://twitter.com/newsbot/status/example2",
    },
    {
      id: "n3",
      label: "Shared in group",
      platform: "facebook",
      date: "2025-12-03",
      url: "https://facebook.com/groups/example3",
    },
    {
      id: "n4",
      label: "CNN iReport submission",
      platform: "news",
      date: "2025-12-05",
      url: "https://cnn.com/article/example4",
    },
    {
      id: "n5",
      label: "@viral.pics story",
      platform: "instagram",
      date: "2025-12-06",
      url: "https://instagram.com/p/example5",
    },
    {
      id: "n6",
      label: "Fact-check debunk",
      platform: "news",
      date: "2025-12-08",
      url: "https://snopes.com/fact-check/example6",
    },
  ],
  edges: [
    { from: "src", to: "n1" },
    { from: "src", to: "n2" },
    { from: "n1", to: "n3" },
    { from: "n2", to: "n4" },
    { from: "n3", to: "n5" },
    { from: "n4", to: "n6" },
  ],
  summary: {
    total_matches: 6,
    platforms: ["reddit", "twitter", "facebook", "news", "instagram"],
  },
};

// Default export is the medium scenario
export default MOCK_SPREAD_MEDIUM;
