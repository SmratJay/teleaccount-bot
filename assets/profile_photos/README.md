# Profile Photos Directory

This directory contains profile photos that will be randomly assigned to accounts after they are sold.

## How to Add Photos

1. Add image files in the following formats:
   - `.jpg` or `.jpeg`
   - `.png` 
   - `.webp`

2. Recommended specifications:
   - Size: 512x512 pixels or larger
   - Quality: High resolution, clear images
   - Content: Generic, neutral profile photos (not personal photos)

3. Naming convention:
   - Use descriptive names like: `avatar1.jpg`, `profile_male_1.png`, etc.
   - Avoid special characters in filenames

## Current Photos

The system will automatically detect and use any image files placed in this directory.

To check available photos, the bot will scan for files with supported extensions.

## Usage

When an account is sold, the system will:
1. Delete the current profile photo
2. Randomly select a photo from this directory
3. Upload it as the new profile photo
4. Log the change in the activity log

## Important Notes

- Ensure you have rights to use any photos you add
- Use generic/stock photos, not personal images
- The more variety you provide, the better the randomization
- Photos should be appropriate and professional