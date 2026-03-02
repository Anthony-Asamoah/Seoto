# Seoto

A Django web application.

---

## Management Commands

### Blog

#### `migrate_blog_to_richtext`
Converts existing blog post content from Markdown to HTML. Safe to re-run — skips posts whose content already appears to be HTML.

```bash
python manage.py migrate_blog_to_richtext --dry-run   # preview
python manage.py migrate_blog_to_richtext
```

#### `sanitize_tags_and_groups`
Normalizes existing blog tags to **singular lowercase** and read groups to **plural lowercase**. Merges duplicates that arise after normalization by reassigning all post/member references before deleting the stale record.

```bash
python manage.py sanitize_tags_and_groups --dry-run   # preview
python manage.py sanitize_tags_and_groups
```

#### `cleanup_orphan_blog_images`
Scans the `blog/images/` directory in storage and deletes any image files not referenced in any live post. Run after bulk post deletions or as periodic maintenance.

```bash
python manage.py cleanup_orphan_blog_images --dry-run   # preview
python manage.py cleanup_orphan_blog_images
```

---

### Accounts

#### `migrate_accounts_images_to_s3`
Migrates user profile images from local storage to S3. Requires `MEDIA_STORAGE=AWS` to be configured.

```bash
python manage.py migrate_accounts_images_to_s3
```

#### `generate_profile_thumbnails`
Generates or regenerates 80×80 JPEG thumbnails for all user profile pictures that are missing a thumbnail.

```bash
python manage.py generate_profile_thumbnails
```

---

### Author

#### `migrate_author_images_to_s3`
Migrates author profile images from local storage to S3. Requires `MEDIA_STORAGE=AWS` to be configured.

```bash
python manage.py migrate_author_images_to_s3
```

#### `seed_hobbies`
Seeds the database with a default set of hobby options for author profiles.

```bash
python manage.py seed_hobbies
```

---

### Foodie

#### `migrate_foodie_images_to_s3`
Migrates meal images from local storage to S3. Requires `MEDIA_STORAGE=AWS` to be configured.

```bash
python manage.py migrate_foodie_images_to_s3
```

#### `generate_foodie_thumbnails`
Generates or regenerates thumbnails for all meal images that are missing one.

```bash
python manage.py generate_foodie_thumbnails
```

---

### Theme

#### `seed_themes`
Seeds the database with the 5 official theme presets (Light, Dark, High Contrast, Ocean, Forest). Safe to re-run — uses `update_or_create`.

```bash
python manage.py seed_themes
```

---

### PWA

#### `generate_vapid_keys`
Generates a VAPID key pair for web push notifications and prints the values to add to `.env`.

```bash
python manage.py generate_vapid_keys
```
