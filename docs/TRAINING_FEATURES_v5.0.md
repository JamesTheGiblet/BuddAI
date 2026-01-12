# BuddAI v5.0 Training Features

## Overview

BuddAI v5.0 introduces modular training strategies, allowing for dynamic knowledge acquisition from both local files and remote sources. This decouples the "intelligence" from the core code, enabling easier sharing and bulk loading of rules.

---

## 1. Public Knowledge Base (GitHub Gists)

BuddAI can now "subscribe" to external rule sets hosted on GitHub Gists or any raw text URL. This allows you to maintain a "cloud brain" of rules that can be imported into any BuddAI instance.

### Usage

```bash
/train public_db <RAW_URL>
```

### How to Create a Knowledge Base

1. **Create a Gist:** Go to [gist.github.com](https://gist.github.com).
2. **Add Rules:** Write your rules. You can use the `/teach` prefix or just write plain sentences. Comments starting with `#` are ignored.
3. **Get Raw URL:** Click the **Raw** button to get the direct text URL.
4. **Train:** Feed this URL to BuddAI.

**Example File Content:**

```text
# My Python Standards
/teach Prefer f-strings over .format()
/teach Use type hints for all function arguments
/teach For file operations, always use 'with open(...) as f'
```

---

## 2. Auto-Discovery (Local Training Folder)

BuddAI can automatically detect and import training files placed in the `training/` directory. This is ideal for bulk-loading rules from project notes, failure logs, or exported chat histories.

### Usage

```bash
/train auto_discovery
```

### How it Works

1. **Place Files:** Drop any `.txt` file into the `buddAI/training/` folder.
    * *Example:* `buddAI/training/3d_printer_failures.txt`
2. **Format:** Ensure rules you want explicitly learned start with `/teach`.
3. **Run Command:** BuddAI scans the directory, parses the files, and imports new rules.
4. **Deduplication:** The system automatically skips rules it has already learned to prevent database bloating.

**Target Directory:**
`.../buddAI/training/*.txt`

---

## 3. Extensibility

New strategies can be added by placing a Python script in `buddAI/training/strategies/`. The system uses reflection to auto-discover new strategy classes at runtime.
