# BiteBuilder

A FastAPI-based web application with user authentication, blog posts, and AI-powered recipe features.

## Features

- User registration, login, and profile management
- Blog post creation and browsing
- Recipe search by ingredients (Spoonacular API)
- AI-powered recipe suggestions from food images (Google Gemini)
- SQLite database (auto-created on first run)

---

## Prerequisites

| Requirement | Windows | macOS |
|---|---|---|
| **Python 3.13+** | [python.org/downloads](https://www.python.org/downloads/) — check "Add to PATH" during install | `brew install python@3.13` (requires [Homebrew](https://brew.sh)) |
| **Git** | [git-scm.com/download/win](https://git-scm.com/download/win) | `brew install git` or `xcode-select --install` |
| **uv** (package manager) | `pip install uv` in PowerShell | `brew install uv` or `pip install uv` |
| **Google Gemini API key** | Get from [aistudio.google.com](https://aistudio.google.com/app/apikey) | Same |
| **Spoonacular API key** | Get from [spoonacular.com/food-api](https://spoonacular.com/food-api/console#Dashboard) | Same |

---

## Installation

### 1. Clone the repository

**Windows (PowerShell / CMD):**
```powershell
git clone https://github.com/jiyasharmainbox-beep/BiteBuilder.git
cd BiteBuilder
```

**macOS (Terminal):**
```bash
git clone https://github.com/jiyasharmainbox-beep/BiteBuilder.git
cd BiteBuilder
```

### 2. Create and activate the virtual environment

**Windows:**
```powershell
uv venv .venv
.venv\Scripts\Activate.ps1
```
> If you get a script execution policy error, run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**macOS:**
```bash
uv venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Create the `.env` file

Create a file named `.env` in the project root:

```env
SECRET_KEY=your_random_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_BASE_URL=http://localhost:8000
SPOONACULAR_API_KEY=your_spoonacular_api_key_here
```

> **Tip:** Generate a secure `SECRET_KEY`:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

### 5. Set the Gemini API key

Open `routers/recipes.py` and update line 13:
```python
YOUR_GEMINI_API_KEY = "your_gemini_api_key_here"
```

### 6. Create required media directory

**Windows:**
```powershell
mkdir media\profile_pics
```

**macOS:**
```bash
mkdir -p media/profile_pics
```

### 7. (Optional) Populate the database with sample data

```bash
python populate_db.py
```

---

## Usage

```bash
uvicorn main:app --reload
```

Open your browser at: [http://localhost:8000](http://localhost:8000)

> The database (`blog.db`) is created automatically on first run — no database server needed.

---

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

MIT License - see LICENSE file for details

## Contact

For questions or suggestions, please open an issue.

## Bibliography
API for recipe search by ingredients:
https://spoonacular.com/food-api/docs#Search-Recipes-by-Ingredients


Styling:
https://getbootstrap.com/docs/5.3/components/buttons/

Regular Expressions :
https://regexr.com

APIs and Postman :
https://www.postman.com/what-is-an-api/
