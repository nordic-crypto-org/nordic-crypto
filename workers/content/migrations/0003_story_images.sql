-- One generated illustration per story. The PNG lives in R2 (not in git).
-- This table is the public record: story id, object key, style, prompt, created time.
-- The style library and the recent-style list live here too, so a new story
-- does not repeat a style that was just used, and a topic can add a style.
-- Prompts are generation notes. The public API does not return them.
-- Rows may be replaced once, when a headline-card fallback is upgraded to a
-- generated picture. They are not a review audit.

CREATE TABLE IF NOT EXISTS story_images (
  story_id TEXT PRIMARY KEY,
  r2_key TEXT NOT NULL,
  style_id TEXT NOT NULL,
  prompt TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('ai', 'fallback')),
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  content_type TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS story_image_styles (
  id TEXT PRIMARY KEY,
  prompt TEXT NOT NULL,
  origin TEXT NOT NULL CHECK (origin IN ('base', 'topic')),
  topic TEXT,
  technique TEXT,
  story_id TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS story_image_style_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  recent TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS story_images_style ON story_images (style_id);

INSERT INTO story_image_style_state (id, recent) VALUES (1, '[]')
  ON CONFLICT(id) DO NOTHING;

INSERT INTO story_image_styles (id, prompt, origin, topic, technique, story_id, created_at) VALUES
  ('photoreal-editorial', 'photoreal editorial photography, sharp detail, natural Nordic light, magazine cover quality', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z'),
  ('watercolour', 'loose watercolour painting on textured paper, soft washes, visible brush edges', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z'),
  ('flat-vector', 'flat vector illustration, bold shapes, limited palette, clean edges, poster design', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z'),
  ('isometric-3d', 'isometric 3D illustration, soft studio lighting, clean geometric forms', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z'),
  ('neon-cyberpunk', 'neon cyberpunk night scene, teal and gold glow, rain-slick streets, futuristic Nordic city', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z'),
  ('paper-collage', 'hand-cut paper collage, layered coloured card stock, craft texture, studio photo of the collage', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z'),
  ('ink-sketch', 'black ink sketch with sparse gold wash accents, cross-hatching, notebook page feel', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z'),
  ('retro-poster', '1960s travel poster, silk-screen print look, bold shapes, no lettering', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z'),
  ('minimal-geometric', 'minimal geometric composition, large flat colour fields, Bauhaus-inspired shapes', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z'),
  ('cinematic-night', 'cinematic night photography, deep teal shadows, warm gold highlights, shallow depth of field', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z'),
  ('ligne-claire', 'ligne claire Franco-Belgian comic illustration, clean black outlines, flat bright colours, even lighting, original adult characters only, never any copyrighted comic characters', 'base', NULL, NULL, NULL, '2026-11-06T00:00:00Z')
  ON CONFLICT(id) DO NOTHING;

INSERT INTO schema_meta (key, value) VALUES ('version', '3')
  ON CONFLICT(key) DO UPDATE SET value = excluded.value;
