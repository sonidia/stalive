# 🔄 Proxer

A sleek, dark-themed desktop application for fetching, managing, and auto-rotating residential proxies from a **Cliproxy** API server. Built with Python and PySide6.

---

## ✨ Features

- 🌍 **Multi-country proxy filtering** — Filter by country, state/province, city, and ISP/network
- 🔍 **Proxy retrieval** — Fetch one or multiple proxies in a single request
- 🃏 **Proxy cards** — Each proxy is displayed as a rich card with status, ping, and metadata tags
- ⚡ **Live proxy checking** — Test if a proxy is alive with real-time ping measurement
- ↻ **Proxy refresh** — Re-fetch a new proxy for a slot using the same parameters
- ⚡ **Bulk check / Bulk refresh** — Check or refresh all proxies at once
- ⏰ **Auto-rotate** — Automatically check and refresh dead proxies on a configurable interval (5 – 300 s)
- 📋 **One-click copy** — Copy any proxy to clipboard instantly
- 💾 **Persistent cache** — Proxies are saved locally in `data.json` and survive app restarts
- 🔗 **Configurable API URL** — Connect to any Cliproxy server by updating the API base URL
- 🚦 **Cliproxy status indicator** — Automatically detects whether Cliproxy is running and locks the UI if it isn't

---

## 🖥️ Screenshot

> Dark-themed, minimal UI with proxy cards, status badges, and action buttons.

---

## 🚀 Getting Started

### Prerequisites

- Python **3.10+**
- [Cliproxy](https://cliproxy.com) running and accessible on your network

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/proxer.git
cd proxer

# Install dependencies
pip install -r requirements.txt
```

### Running

```bash
python app.py
```

---

## 📦 Building an Executable

A PyInstaller build script is included.

```bat
build.bat
```

The spec file (`build.spec`) bundles all assets (including `icon.png` and `data.json`) into a single executable.

---

## ⚙️ Configuration

### API URL

On first launch, the app connects to the default Cliproxy API at:

```
http://192.168.1.29:1998/api
```

You can change this in the **API URL** field at the top of the window and click **💾 Save**. The URL is persisted to `data.json`.

### data.json

All application state is stored in `data.json` next to the executable (or script):

```json
{
  "api_base": "http://192.168.1.13:1998/api",
  "proxies": [
    {
      "ip": "192.168.1.13",
      "port": "2001",
      "country": "US",
      "state": "Florida",
      "city": "Jacksonville",
      "isp": "ATT"
    }
  ]
}
```

---

## 🗺️ Supported Countries & Networks

| Country           | Code | Sample Networks                   |
| ----------------- | ---- | --------------------------------- |
| 🇺🇸 United States  | `US` | ATT, Verizon, T-Mobile, Comcast … |
| 🇦🇺 Australia      | `AU` | Telstra, Optus, Vodafone …        |
| 🇬🇧 United Kingdom | `GB` | BT, Sky, Virgin Media …           |
| 🇩🇪 Germany        | `DE` | Deutsche Telekom, Vodafone …      |
| 🇫🇷 France         | `FR` | Orange, SFR, Bouygues …           |
| 🇯🇵 Japan          | `JP` | NTT, SoftBank, KDDI …             |
| 🇨🇦 Canada         | `CA` | Bell, Rogers, Telus …             |
| 🇸🇬 Singapore      | `SG` | Singtel, StarHub, M1 …            |
| 🇮🇳 India          | `IN` | Jio, Airtel, BSNL …               |
| 🇧🇷 Brazil         | `BR` | Vivo, Claro, TIM …                |

---

## 🧩 Dependencies

| Package    | Version   |
| ---------- | --------- |
| `PySide6`  | >= 6.0.0  |
| `requests` | >= 2.25.0 |

Install all at once:

```bash
pip install -r requirements.txt
```

---

## 📁 Project Structure

```
proxer/
├── app.py            # Main application (UI + logic)
├── shared.py         # Country/state/city/network data
├── data.json         # Persistent storage (API URL + proxy cache)
├── requirements.txt  # Python dependencies
├── build.bat         # Windows build script (PyInstaller)
├── build.spec        # PyInstaller spec file
└── README.md
```

---

## 📄 License

This project is licensed under the terms in [LICENSE](LICENSE).
