# EDI 850 → JSON → ERP API Integration Demo

> **Portfolio Project**: A complete EDI-to-API integration pipeline demonstrating parsing, transformation, and ERP system integration.

---

## Project Overview

This project showcases a modern EDI integration workflow:

1. **Parse** — EDI 850 Purchase Orders → Structured JSON
2. **Transform** — EDI JSON → ERP API Schema
3. **Post** — Send to Mock ERP API
4. **Log** — Track results, errors, and retries
5. **Display** — Simple UI to visualize the pipeline

---

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌──────────┐
│  EDI 850    │ ───▶ │  EDI Parser  │ ───▶ │ Transformer │ ───▶ │ ERP API  │
│  Raw File   │      │  (Custom)    │      │  (Mapper)   │      │  (Mock)  │
└─────────────┘      └──────────────┘      └─────────────┘      └──────────┘
                            │                      │                   │
                            └──────────────────────┴───────────────────┘
                                              │
                                         ┌────▼─────┐
                                         │  SQLite  │
                                         │   Logs   │
                                         └──────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python + FastAPI |
| **EDI Parser** | Custom lightweight parser |
| **Database** | SQLite |
| **Frontend** | Vanilla HTML/CSS/JS |
| **API** | RESTful + JSON |

---

## Project Structure

```
edi-850-json-erp-api-demo
│
├── backend/
│   ├── main.py                   # FastAPI entry point
│   ├── config.py                 # Configuration settings
│   ├── requirements.txt          # Python dependencies
│   │
│   ├── edi_parser/              # EDI 850 parsing logic
│   ├── transformer/             # JSON transformation layer
│   ├── mock_erp_api/            # Mock ERP endpoints
│   ├── processor/               # Integration orchestrator
│   └── db/                      # SQLite persistence
│
├── frontend/
│   ├── index.html               # Main UI
│   ├── style.css                # Styling
│   └── app.js                   # Upload + display logic
│
├── sample_data/
│   └── sample_850.edi           # Test EDI file
│
└── logs/                        # Runtime logs
```

---

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd edi-850-json-erp-api-demo

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Run the application
./run.sh
```

### Access the Application

- **Frontend UI**: open `frontend/index.html` in your browser
- **API Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

---

## Usage

1. Open the web UI
2. Upload an EDI 850 file (use `sample_data/sample_850.edi`)
3. View the parsed JSON structure
4. See the transformed ERP payload
5. Check the mock API response

---

## 📸 Screenshots

Below are key screenshots demonstrating the full functionality of the EDI 850 → JSON → ERP API Integration Demo.

---

### **1. Service Health Check**
Verifies that the backend API is running and reachable.

![Health Check](images/health-check.png)

---

### **2. Auto-Generated API Documentation (Swagger UI)**
Shows the full FastAPI surface, available endpoints, and automatic schema documentation.

![API Docs](images/api-docs.png)

---

### **3. Web UI – File Upload Interface**
The lightweight frontend where users upload EDI 850 files for processing.

![UI Upload](images/ui-upload.png)

---

### **4. End-to-End Processing – EDI → JSON → ERP API Response**
This screenshot demonstrates the full pipeline:
- EDI 850 parsed into structured JSON  
- Transformed into ERP-ready schema  
- Submitted to the mock ERP API  
- API response displayed in the UI  

![Pipeline Result](images/pipeline.png)

---

These screenshots visually validate the complete integration workflow and provide a clear overview of the system from UI to backend API.

---

## Key Concepts Demonstrated

- **EDI Parsing**: Understanding X12 structure, segments, loops
- **Data Transformation**: Mapping between different schemas
- **API Integration**: RESTful patterns, error handling, retries
- **Orchestration**: Pipeline design, logging, state management
- **Full-Stack Development**: Backend + Frontend + Database

---

## Contact

**Brian Hughes**

[GitHub](https://github.com/itsbrianhughes) | [LinkedIn](https://linkedin.com/in/b-hughes)

---

## License

MIT License - Feel free to use this project for learning and portfolio purposes.
