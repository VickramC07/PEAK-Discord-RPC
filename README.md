# DO NOT USE, DEPRECATED UNTILL FURTHER NOTICE **PEAK-Discord-RPC**  
*Bring your PEAK gameplay to life on Discord with real-time, detailed activity status.*

## Overview  
PEAK-Discord-RPC enhances Discord Rich Presence for the game **PEAK**, displaying **accurate, real-time game details** along with a **polished and engaging activity status**.  
It pulls live information from the game’s logs, displays player and session details, and even supports custom branding options.

---

## Features  

### **Accurate Game Details**  
- Displays your **current in-game activity** directly on Discord.  
- Shows session time, current state, and player information.  

![Game Details Example](docs/images/Peak_Activity_Example.png)

---

### **Auto Character Display**  
- Reads your PEAK character’s **appearance and attributes** from the log.  
- Automatically generates a **custom character preview image**.  

![Auto Character Creation](docs/images/Peak_Auto_Generated_Character.png)

---

### **Player Tracking**  
- Shows **player count** in your session.   

![Player List](docs/images/Peak_Player_Count.png)

---

### **Custom Buttons & Branding**  
- Add your own **social link button** with a custom name and URL.  
- Optionally display a **GitHub link** to the project creator.
- *Note that you will not be able to see your own buttons but others will*

![Custom Buttons](docs/images/Peak_Buttons.png)

---

### **Quick Launch Support**  
- [NOT RECCOMENDED] Optionally launch PEAK directly via Steam from the script.
- **DISCLAIMER:** it will always run in Vulkan due to the default PEAK dll file being configured as such. To change this you can go to https://github.com/CyR1en/UnityPlayerPatcher.
- **Run it from Steam in DX12 first to ensure the RPC works correctly.**
- Supports **log refresh detection** to ensure accurate data after launching.

---

### **Error Handling & Logging**  
- Comprehensive exception handling with error popups.  
- Saves error logs automatically for troubleshooting.  
- Opens log files for you when errors occur (when running as an executable).  

---

## Gallery  
*(Replace placeholders with screenshots from your running application)*  

1. **Main Discord Rich Presence view:**  
   ![Main RPC Example](docs/images/Main_Prescence_View.png)  

2. **Character Preview:**  
   ![Character Preview Example](docs/images/Character_Preview.png)  

3. **Custom Buttons:**  
   ![Buttons Example](docs/images/Peak_Buttons.png)  

---

## 📦 Installation  

1. Download the latest release from the **[Releases](https://github.com/VickramC07/PEAK-Discord-RPC/releases)** page.  
2. Run the executable while PEAK is running(preferably in DX12).  
3. Enjoy your upgraded Discord Rich Presence!  
