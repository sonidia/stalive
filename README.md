# Proxy Fetcher

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)](https://pypi.org/project/PySide6/)

A modern, dark-themed desktop application for fetching, managing, and auto-rotating residential proxies from Cliproxy API servers. Built with Python and PySide6 for a seamless user experience.

## 📋 Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [Building](#-building)
- [Supported Countries](#-supported-countries)
- [Project Structure](#-project-structure)
- [Dependencies](#-dependencies)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### Core Functionality

- 🌍 **Multi-country proxy filtering** - Filter proxies by country, state/province, city, and ISP/network
- 🔍 **Flexible proxy retrieval** - Fetch single or multiple proxies in one request
- 🃏 **Rich proxy cards** - Visual proxy display with status, ping, and metadata tags
- ⚡ **Real-time proxy checking** - Live ping measurement and connectivity testing
- ↻ **Smart proxy refresh** - Re-fetch proxies using the same parameters
- ⚡ **Bulk operations** - Check or refresh all proxies simultaneously

### Automation & Management

- ⏰ **Auto-rotation** - Automatic proxy checking and refreshing on configurable intervals (5-300 seconds)
- 📋 **One-click copy** - Instant clipboard copying of proxy details
- 💾 **Persistent storage** - Local caching in JSON format with app restart persistence
- 🔗 **Flexible API configuration** - Connect to any Cliproxy server instance
- 🚦 **Status monitoring** - Real-time Cliproxy server status detection with UI locking

### User Experience

- 🖥️ **Modern dark UI** - Sleek, professional interface design
- 📊 **Statistics tracking** - Comprehensive usage and performance metrics
- 🔧 **Intuitive configuration** - Easy-to-use settings and preferences
- 📱 **Responsive design** - Optimized for various screen sizes

## 🛠️ Prerequisites

- **Python 3.10 or higher**
- **Cliproxy server** running and accessible on your network
- **Windows/Linux/macOS** (cross-platform support)

## 🚀 Installation

### Option 1: Clone and Run (Development)

```bash
# Clone the repository
git clone https://github.com/sonidia/proxy.git
cd proxy

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Option 2: Download Executable (Production)

1. Download the latest release from [Releases](https://github.com/sonidia/proxy/releases)
2. Extract the ZIP file
3. Run `ProxyFetcher.exe` (Windows) or `ProxyFetcher` (Linux/macOS)

## 📖 Usage

### Basic Usage

1. **Launch the application** by running `python app.py` or the executable
2. **Configure API URL** if your Cliproxy server is not on the default address
3. **Select proxy parameters** using the dropdown menus for country, state, city, and network
4. **Fetch proxies** using the "Get Proxy" button
5. **Monitor status** through the visual proxy cards showing ping and connectivity
6. **Copy proxy details** by clicking the copy button on any proxy card

### Advanced Features

- **Auto-rotation**: Enable automatic proxy refreshing in the settings
- **Bulk operations**: Use "Check All" or "Refresh All" for multiple proxies
- **Statistics**: View detailed usage statistics in the stats modal
- **Custom intervals**: Configure auto-rotation timing (5-300 seconds)

### Configuration File

The application stores all settings in `data.json`:

```json
{
  "api_base": "http://localhost:1998/api",
  "proxies": [
    {
      "ip": "192.168.1.13",
      "port": "2001",
      "country": "US",
      "state": "Florida",
      "city": "Jacksonville",
      "isp": "ATT",
      "ping": 45,
      "status": "alive"
    }
  ],
  "auto_rotate_interval": 60,
  "theme": "dark"
}
```

## ⚙️ Configuration

### API Configuration

- **Default API URL**: `http://localhost:1998/api`
- **Custom servers**: Enter any Cliproxy API endpoint in the UI
- **Network requirements**: HTTP/HTTPS access to Cliproxy server

### Application Settings

- **Auto-rotation interval**: 5-300 seconds
- **Theme**: Dark (default) or Light
- **Ping timeout**: Configurable timeout for connectivity tests
- **Bulk operation limits**: Maximum concurrent operations

## 🏗️ Building

### Windows Executable

```batch
# Run the build script
build.bat

# Or manually with PyInstaller
pyinstaller --onefile --windowed --name ProxyFetcher app.py
```

### Cross-Platform Build

```bash
# Install PyInstaller
pip install pyinstaller

# Build for current platform
pyinstaller build.spec

# Build for specific platforms (requires corresponding Python environment)
# Windows: pyinstaller --onefile --windowed --name ProxyFetcher app.py
# Linux: pyinstaller --onefile --name ProxyFetcher app.py
# macOS: pyinstaller --onefile --name ProxyFetcher app.py
```

The build process includes:

- Single executable file generation
- All dependencies bundled
- Icon and data files included
- Optimized for distribution

## 🌍 Supported Countries

| Country           | Code | Major Networks                             |
| ----------------- | ---- | ------------------------------------------ |
| 🇺🇸 United States  | `US` | AT&T, Verizon, T-Mobile, Comcast, Spectrum |
| 🇦🇺 Australia      | `AU` | Telstra, Optus, Vodafone, Tangerine        |
| 🇬🇧 United Kingdom | `GB` | BT, Sky, Virgin Media, TalkTalk            |
| 🇩🇪 Germany        | `DE` | Deutsche Telekom, Vodafone, O2             |
| 🇫🇷 France         | `FR` | Orange, SFR, Bouygues, Free                |
| 🇯🇵 Japan          | `JP` | NTT, SoftBank, KDDI, au                    |
| 🇨🇦 Canada         | `CA` | Bell, Rogers, Telus, Shaw                  |
| 🇸🇬 Singapore      | `SG` | Singtel, StarHub, M1                       |
| 🇮🇳 India          | `IN` | Jio, Airtel, BSNL, Vi                      |
| 🇧🇷 Brazil         | `BR` | Vivo, Claro, TIM, Oi                       |

_Additional countries and networks are supported through the Cliproxy API._

## 📁 Project Structure

```
proxy/
├── app.py                 # Main application entry point and UI
├── shared.py              # Shared data and constants (countries, networks)
├── utils.py               # Utility functions and helpers
├── stats.py               # Statistics collection and display modal
├── ping.py                # Network ping testing functionality
├── data.json              # Application configuration and proxy cache
├── requirements.txt       # Python dependencies
├── build.bat              # Windows build script
├── build.spec             # PyInstaller specification file
├── LICENSE                # MIT License
└── README.md              # This file
```

## 📦 Dependencies

| Package       | Version   | Purpose                            |
| ------------- | --------- | ---------------------------------- |
| `PySide6`     | >= 6.0.0  | Qt6 Python bindings for GUI        |
| `requests`    | >= 2.25.0 | HTTP library for API communication |
| `pyinstaller` | >= 5.0.0  | Application packaging (build only) |

### Installing Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install pyinstaller black flake8 pytest
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run tests: `python -m pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Add docstrings to functions and classes
- Run `black` for code formatting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Cliproxy](https://cliproxy.com) for the residential proxy infrastructure
- [PySide6](https://wiki.qt.io/Qt_for_Python) for the excellent GUI framework
- [Python](https://python.org) for the amazing programming language

---

**Made with ❤️ by [Tran Nguyen Thuong Truong](https://github.com/thuongtruong109)**
