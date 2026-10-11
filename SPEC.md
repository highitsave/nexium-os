PROJECT: NEXIUM OS - COMPLETE LINUX DISTRIBUTION

Build a real, bootable Linux operating system called Nexium OS. This must be an actual Linux distribution, NOT an HTML mockup, fake desktop, website, or virtual machine interface.

1. CORE REQUIREMENTS
Name: Nexium OS. Architecture: AMD64/x86_64. Base: Debian Stable. Build system: Debian live-build. Output: NexiumOS.iso. Maximum ISO size: UNDER 1 GB. Target ISO size: 700-900 MB. Boot method: USB/hybrid ISO. Primary purpose: lightweight, polished desktop operating system.
The ISO must contain a real Linux kernel, bootloader, compressed root filesystem, desktop environment, and required applications. It must boot on compatible computers without automatically modifying their internal drives. Prioritize reliability, low resource usage, and real functionality.

2. DESKTOP DESIGN
Look like macOS Golden Gate combined with Ubuntu, with its own Nexium branding. Include: macOS-style bottom dock; top system panel; rounded application windows; smooth but lightweight animations; Nexium-branded boot splash; macOS Golden Gate-inspired wallpaper; consistent icon theme; light and dark themes if practical; functional application launcher; working window controls; desktop right-click options; system tray for network, sound, battery, notifications where supported; a welcome screen for new users. The dock must launch real applications. Apps must open in their own proper windows and must not all open the same page. Users must move, minimize, maximize, close windows, switch apps, use keyboard shortcuts. Use a lightweight DE (XFCE or LXQt or similar). Do not sacrifice stability for visual effects.
IMPORTANT: I WILL PROVIDE THE ICON PACK SEPARATELY. WAIT FOR THE ICON PACK BEFORE FINALIZING THE ICON LAYOUT. USE MY PROVIDED ICONS RATHER THAN REPLACING THEM WITH RANDOM ONES.

3. DEFAULT APPLICATION DOCK
1. Files (file manager). 2. Browser. 3. Terminal. 4. Nexium Messages. 5. Nexium Calls. 6. Settings. 7. NEXIUM VAULT (application center). 8. Text Editor. 9. System Monitor. 10. Trash. Every application must have its own real functionality and appropriate icon. Show running-app indicators. Allow pin/unpin where practical. No duplicate browsers or fake applications.

4. NEXIUM MESSAGES
Real desktop messaging app inspired by Apple's Messages. Interface: sidebar with conversations; contact names and profile pictures; recent message previews; unread indicators; new-conversation button; chronological history; distinct sent/received bubbles; timestamps; text input; send button; attachments where practical; emoji where practical; delivery indicators; notifications for incoming messages.
Flow: user creates an account or enters demo mode; selects a contact; writes and sends; app creates a unique message ID; message goes to the backend; server authenticates sender and processes it; stores it for the recipient; recipient receives it when connected; app updates delivery status when confirmation is available; conversation history persists after restart.
Persistent history: store local conversation data in SQLite or similar. Support contacts, conversations, message history, timestamps, message IDs, delivery status, unread counts, conversation names. Messages must not disappear when the app closes.
Offline: if a recipient is offline, the server queues their messages and delivers on reconnect. Distinguish message sent, server acceptance, message delivered, message read (if read receipts implemented). Never claim a message was delivered unless delivery was actually confirmed.
Backend: appropriate messaging server and secure protocol. Provide a local demo mode for testing without a server. The messaging server must be deployable separately from the desktop ISO. Do not pretend messages can travel between different people without a working backend.

5. NEXIUM CALLS
Dedicated calling app integrated with Messages. Interface: contact list; call button; incoming and outgoing call screens; answer/decline; call timer; mic mute; audio-device selection where supported; call history; connection status; end-call; incoming-call notifications; clear error messages on failure.
Real calling via WebRTC or similar. Implement/integrate: call signaling; user authentication; audio capture; audio playback; connection negotiation; network traversal; error handling; incoming-call notifications. Typical call: caller selects contact; Nexium sends a call invitation via the signaling service; recipient gets an incoming call notification; recipient accepts or declines; if accepted devices negotiate a connection; audio streams; either side can end. Include relay infrastructure if network restrictions prevent direct connections. Clearly indicate when the mic is active. Do not simulate successful calls. If calling infrastructure is not configured, explain what is missing.
Messages/Calls integration: both share the same contacts and accounts. A user can open a conversation and press a call button to start a voice call; after the call they return to the same conversation.

6. NEXIUM ACCOUNTS AND SECURITY
Provide: registration or sign-in; display names; unique account identifiers; contact management; profile pictures; notification settings; local demo accounts. Security: secure network connections; never store passwords as plain text; protect auth tokens; enforce access controls; prevent unauthorized access to conversations; rate limiting; avoid logging passwords or private messages; request permissions appropriately; keep admin privileges separate. E2E encryption may arrive in a later milestone; do not claim it exists unless implemented and tested.

7. NEXIUM VAULT
An application center. Discover and install software through an appropriate package-management backend. Include: app names; icons; descriptions; install status; progress indicators; error messages; launch buttons after successful install. Use Debian package management where appropriate. Do not claim an app installed unless the package manager confirms success. Use proper system authorization. Keep the initial catalog lightweight.

8. ICONS AND BRANDING
I WILL PROVIDE THE ICON PACK AND VISUAL REFERENCES. Use supplied assets throughout the desktop. Requirements: preserve original artwork; consistent icon sizes; no stretching; suitable resolutions; fallback icons only when necessary; icons visible against the theme. Apply Nexium branding to: boot splash; wallpaper; welcome screen; dock and launcher where appropriate; system information page; app branding where appropriate. Do not finalize the icon arrangement until the icon pack is supplied. The desktop should feel cohesive.

9. KEEP THE ISO UNDER 1 GB
Final ISO MUST be under 1 GB; aim for ~700-900 MB. Use: minimal Debian base; live-build; SquashFS compression; careful package list; lightweight DE; one browser; only essential default apps; minimal background services. No unnecessary dev toolchains, duplicate apps, or large suites. Install extras via NEXIUM VAULT, not the ISO. Keep messaging/calling servers separate from the ISO. Measure ISO size throughout. Do not blindly strip networking components, audio libraries, drivers, firmware, or system deps just to shrink it. The ISO must stay functional. If the chosen browser is too large, compare alternatives and measure their real installed size first.

10. USB BOOT AND LIVE MODE
Bootable hybrid ISO for USB writing. Nexium-branded boot menu; default option starts Nexium OS. Boot process: load kernel; init hardware/drivers; mount the compressed live filesystem; start the graphical environment; load the Nexium desktop; display dock and system panel. The default live session must not automatically erase or modify the internal drive. Support optional USB persistence if practical. Any included installer must clearly identify the target drive and require confirmation before destructive operations.

11. DEFAULT SYSTEM APPLICATIONS
System: file manager; terminal; settings; system monitor; text editor; archive manager. Internet: browser; network manager. Communication: Nexium Messages; Nexium Calls. Utilities: screenshot utility; image viewer; audio controls; USB storage support. Avoid multiple apps serving the same purpose.

12. TERMINAL AND ADMINISTRATION
Real Linux terminal with a standard shell. Support: file operations; directory navigation; process inspection; network diagnostics; package management; admin commands through sudo where configured. Do not run the whole graphical desktop as root. Use a normal user account and elevate when needed. Document what persists and what disappears after reboot in live mode.

13. PERFORMANCE
Keep it lightweight and responsive. Test: boot time; idle RAM; CPU usage; desktop responsiveness; app launch times; browser performance; Wi-Fi; audio playback; microphone; USB storage; shutdown; restart. Target usability on 4 GB RAM machines. Avoid unnecessary background processes and heavy animations.

14. PROJECT STRUCTURE
Organized reproducible tree like: NexiumOS/ with README.md, build.sh, config/ (package-lists/, hooks/, includes.chroot/), branding/ (wallpaper/, icons/, boot/), desktop/ (dock/, panel/, themes/), apps/ (messages/, calls/, vault/), services/ (networking/), tests/, output/ (NexiumOS.iso). Adapt as necessary. Keep client apps, backend services, desktop config, and build scripts organized.

15. BUILD AUTOMATION
Reproducible build script that: checks dependencies; checks disk space; configures live-build; installs required packages; applies branding; configures the desktop; builds the ISO; verifies ISO size; checks for expected boot files; generates a checksum; preserves build logs; reports errors accurately; saves the ISO to output/. On failure return a nonzero exit code and explain the failure. Do not report success just because an ISO exists. Document all required dependencies and commands.

16. TESTING CHECKLIST
Verify: ISO builds without errors; under 1 GB; expected boot files present; boots in a VM; USB boot works on compatible hardware; desktop loads correctly; dock launches correct apps; windows move and resize; file manager works; terminal works; networking works where supported; browser loads sites; Messages opens; message history persists after restart; real messaging works when the backend is configured; Calls opens; real voice calls work when services are configured; microphone works on supported hardware; notifications work; USB storage accessible; shutdown works; restart works; no credentials exposed in logs; apps do not falsely report success. Document features needing external services or extra configuration.

17. DEVELOPMENT PHASES
Phase 1 Bootable Foundation: Debian live system; bootloader; lightweight desktop; networking, terminal, file manager; ISO under 1 GB; verify USB boot.
Phase 2 Nexium Desktop: branding; supplied icon pack; dock and top panel; themes and window decorations; test desktop interactions.
Phase 3 Core Applications: browser; system settings; NEXIUM VAULT; apps open independently; keyboard shortcuts and window management.
Phase 4 Messaging: Messages interface; accounts and contacts; messaging backend; persistent history; sync, offline delivery, notifications.
Phase 5 Calling: call signaling; audio devices; real one-to-one voice calls; incoming-call notifications; test across devices and networks.
Phase 6 Final Release: rebuild clean; verify ISO size; test desktop/apps; test booting; hardware compatibility; document limitations; final ISO and checksum.

18. FINAL DELIVERABLES
1. complete source project. 2. build script. 3. package lists and desktop config. 4. Nexium app source. 5. messaging backend components if implemented. 6. calling backend components if implemented. 7. build instructions. 8. testing instructions. 9. bootable NexiumOS.iso under 1 GB. 10. ISO checksum. 11. known-limitations doc. Do not deliver only a mockup, screenshot, web page, or untested script. If the environment cannot build the ISO, say so and provide the complete reproducible project and instructions. Never pretend the ISO was built when it was not.

FINAL OBJECTIVE: a genuinely bootable, usable Nexium Linux distribution with a polished macOS Golden Gate-inspired desktop, Ubuntu-like functionality, custom Nexium branding, working core apps, persistent messaging, real internet voice calling, and an ISO under 1 GB, prioritizing reliability, security, real functionality, and a consistent UX. Start with the minimal bootable OS, then layer desktop customization and communication apps in stages.
