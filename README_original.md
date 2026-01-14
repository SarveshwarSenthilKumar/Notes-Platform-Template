# LexiconJuris

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🏛️ Specialized Legal Version

LexiconJuris is a specialized version of Lexicon, tailored specifically for legal professionals and students. It provides comprehensive tools for managing legal terms, case notes, and case law references with advanced search capabilities and user authentication. LexiconJuris streamlines legal research and case management through an intuitive interface and powerful search functionality.

> ℹ️ **Note**: A generalized version of this application, called **Lexicon**, will be available soon for broader knowledge management use cases beyond the legal domain.

## ✨ Features

### 📚 Legal Dictionary
- Add, edit, and search legal terms and definitions
- View entry history and related terms
- Public and private entry views
- Advanced search with filtering options
- Bulk import/export functionality
- Version history for each entry

### 📝 Case Notes Management
- Create and organize case notes with rich text formatting
- Advanced text editor with formatting tools
- Tagging and categorization system
- Full-text search with highlighting
- Note templates for common legal documents
- Export notes to multiple formats (PDF, DOCX)

### 📅 Calendar Integration
- Track important legal dates and deadlines
- Set reminders for court dates and filings
- Recurring events and custom reminders
- Calendar views: day, week, month, agenda
- Integration with external calendar services (coming soon)
- Export calendar events

### 🔐 User Authentication & Security
- Secure user registration and login system
- Role-based access control (Admin, Attorney, Paralegal, Student)
- Session management with configurable timeouts
- Password hashing with bcrypt and salt
- Account recovery options
- Activity logging and audit trails

## 🛠 Tech Stack

### Backend
- **Framework**: Flask (Python 3.8+)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Custom JWT-based authentication
- **API**: RESTful API endpoints
- **Templates**: Jinja2 with template inheritance
- **Background Tasks**: Celery (for future async tasks)
- **AI**: Google Gemini and OpenAI ChatGPT 

### Frontend
- **Core**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Custom CSS with responsive design
- **UI Components**: Custom-built components
- **Form Handling**: Client-side validation
- **AJAX**: For dynamic content loading

### Development Tools
- **Version Control**: Git
- **Package Management**: pip
- **Code Quality**: flake8, black
- **Testing**: pytest, unittest

### Dependencies
See [requirements.txt](requirements.txt) for complete list of Python dependencies.

## 🎯 Getting Started

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/SarveshwarSenthilKumar/LexiconJuris.git
   cd LexiconJuris
   ```

2. **Set up a virtual environment** (recommended)
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```env
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your-secure-secret-key-here
   DATABASE_URL=sqlite:///users.db
   DICTIONARY_DB=sqlite:///dictionary.db
   NOTES_DB=sqlite:///notes.db
   CALENDAR_DB=sqlite:///calendar.db
   ```

5. **Initialize the database**
   ```bash
   python createDatabase.py
   python createDictDB.py
   python createNotesDB.py
   python createCalendarDB.py
   python setup_fts.py  # Set up full-text search
   ```

6. **Run database migrations** (if any)
   ```bash
   flask db upgrade
   ```

7. **Create an admin user**
   ```bash
   python create_user.py --username admin --email admin@example.com --password yourpassword --role admin
   ```

8. **Run the development server**
   ```bash
   flask run
   ```

9. **Access the application**
   Open your web browser and navigate to `http://localhost:5000`
   - Admin dashboard: `http://localhost:5000/admin`
   - API documentation: `http://localhost:5000/api/docs`

## 📁 Project Structure

```
LexiconJuris/
├── app.py                 # Main application entry point
├── requirements.txt       # Python dependencies
├── static/                # Static files (CSS, JS, images)
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript files
│   └── img/              # Images and icons
│
├── templates/             # HTML templates
│   ├── auth/             # Authentication templates
│   ├── dictionary/       # Dictionary views
│   ├── notes/            # Notes management
│   ├── calendar/         # Calendar views
│   └── layouts/          # Base templates
│
├── *.db                  # SQLite database files
├── *.py                  # Main application modules
├── create_*.py           # Database initialization scripts
└── README.md             # This file
```

## 🌟 Features in Detail

### Dictionary Features
- **Comprehensive Legal Terms**: Extensive database of legal terminology
- **Advanced Search**: Search by term, definition, or related concepts
- **Version History**: Track changes to legal definitions over time
- **Import/Export**: Bulk import terms or export your legal dictionary

### Notes Management
- **Rich Text Editing**: Full-featured editor for case notes
- **Organization**: Categorize and tag notes for easy retrieval
- **Templates**: Pre-built templates for common legal documents
- **Search**: Full-text search across all your notes

### Calendar Features
- **Case Management**: Track important dates and deadlines
- **Reminders**: Never miss a court date or filing deadline
- **Multiple Views**: Day, week, month, and agenda views
- **Export**: Sync with external calendar applications

## 🔧 Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Style
This project follows PEP 8 style guidelines. To check your code:
```bash
flake8 .
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - User login
- `GET /auth/logout` - User logout

### Dictionary
- `GET /dictionary` - View all entries
- `POST /dictionary/add` - Add new entry
- `GET /dictionary/<int:entry_id>` - View specific entry
- `POST /dictionary/<int:entry_id>/edit` - Edit entry
- `POST /dictionary/<int:entry_id>/delete` - Delete entry
- `GET /dictionary/search` - Search entries

### Notes
- `GET /notes` - View all notes
- `POST /notes/add` - Add new note
- `GET /notes/<int:note_id>` - View specific note
- `POST /notes/<int:note_id>/edit` - Edit note
- `POST /notes/<int:note_id>/delete` - Delete note

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Built with Flask
- Uses SQLite for database
- Inspired by the needs of legal professionals