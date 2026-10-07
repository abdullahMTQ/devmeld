# DevMeld by Zennor

**Status:** V1 Early Release (Demand Validation Phase)

## About
DevMeld is a developer-focused collaboration platform built with Python and PySide6. It brings together community discussions, direct messaging, and a built-in code editor workspace into a single, cohesive desktop application. 

*Honest Note:* This V1 was shipped quickly to validate our core architecture and gauge community demand. We are actively gathering feedback to shape a massive V2 overhaul.

## Core Features

### 🏠 Home & Profiles
- **Account-Gated Core:** Threads and DMs require an account to ensure secure Firebase interactions.
- **Profile Management:** Customize your avatar (PFP), view your post history, and manage your session.
- **User Profiles:** View other developers' posts, report inappropriate behavior, or initiate a direct message.

### 🧵 Threads & Community
- **Smart Search:** Search for specific posts or find users by typing `@username`.
- **Local Tag Filtering:** Use the dynamic tag belt to filter the feed by specific technologies or topics.
- **Structured Posting:** Create posts with a title, body, and a strict requirement of 1 to 3 tags.
- **Post View & Moderation:** View posts with threaded comments. The 3-dot menu allows authors to delete their posts, while other users can report violations.
- **Notifications:** A dedicated bell icon alerts you when someone comments on your posts.

### 💬 Direct Messages (DMs)
- **Status Indicators:** Color-coded rings around avatars show if a user is currently online or offline.
- **Secure Attachments:** Send files and folders (capped at 35MB for safety). Attachments are never downloaded automatically; they require explicit user confirmation.
- **Chat Management:** 
  - Search bar to quickly find existing conversations.
  - Red dot indicators for unread messages.
  - **Blocking:** Block annoying users via the 3-dot menu on chat cards. *(Note: For safety, only the user who initiated the block can unblock by starting a new conversation).*
  - **Privacy:** A "Hide Strangers" setting to ignore DMs from users you haven't messaged first.

### 💻 Built-in Code Editor
- A fully functional local IDE workspace featuring a file tree, integrated multi-tab terminal, syntax highlighting, problem tracking, and auto-save capabilities.

### 📢 Announcements
- An in-app announcement system accessible from the home screen to keep users updated on platform news and patches.

## Tech Stack
- **Frontend:** Python, PySide6 (Qt for Python)
- **Backend / Cloud:** Firebase Authentication, Firestore, Realtime Database, and Firebase Storage
- **Architecture:** Strict Abstraction Layer Standard (ALS v1.1) separating App, Service, Manager, Adapter, and External layers.

## Roadmap (V2 Plans)
If V1 proves successful, our next major update will include:
1. Full real-time collaborative code editing.
2. Dedicated community servers and group chats.
3. Advanced cross-platform auto-updater.

## How to Run from Source
1. Ensure you have Python 3.10+ installed.
2. Clone this repository.
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `python main.py`

*(Note: Running from source requires your own Firebase configuration to be properly set up in the respective adapter files.)*

## License
This project is **Proprietary**. All rights are reserved by Zennor. 
You may view this code for educational and reference purposes only. Commercial use, modification, or redistribution is strictly prohibited. See the [LICENSE.txt](LICENSE.txt) file for full details.
