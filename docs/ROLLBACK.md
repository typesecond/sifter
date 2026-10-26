# Restore the previous Sifter interface

The original local development checkout retains the complete prior app, source
archive, and wheel under its ignored backups/ directory, plus the Git tag
sifter-studio-v1 and branch backup/sifter-studio-v1. These local backups are not
uploaded with this standalone repository.

This repository's `sifter-studio-v1` tag also preserves the earlier desktop
interface, with inherited copyright notices retained in license files.

To try that source version, first save local changes, then create a branch:

```sh
git switch -c try-studio sifter-studio-v1
```

Return to the current pixel interface with:

```sh
git switch main
```

The previous standalone app can be opened from the original development
checkout's backups/Sifter-studio-v1.app without changing source branches.
