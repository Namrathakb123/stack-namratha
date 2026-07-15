# Stack Education

A web application built with Flask for educational purposes.

## Features

- User Authentication (Signup/Login)
- Student Dashboard & Profile Management
- StackLabs Internship Registration with Payment Tracking
- Admin Panel for Monitoring Applications & Users
- Production-ready for Vercel Deployment

## Technologies Used

- Flask (Python web framework)
- Flask-SQLAlchemy (Database ORM)
- PostgreSQL (Production) / SQLite (Local)
- Tailwind CSS & AOS for animations

## Local Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/abhiramnaik33/stackeducation.git
   cd stackeducation
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

Open your web browser and navigate to `http://localhost:5001` (Note: Default port is changed to 5001).

## Vercel Deployment

This application is configured to run on Vercel as a Serverless Function.

1. **Database Setup**: Create a PostgreSQL database (e.g., on Supabase or Neon).
2. **Environment Variables**: Add the following in Vercel Project Settings:
   - `DATABASE_URL`: Your PostgreSQL connection string.
   - `SECRET_KEY`: A secure random string.
3. **Deploy**: Push to your connected GitHub repository.

## Admin Access

Default Admin Credentials:
- **Email**: `admin@stackeducation.com`
- **Password**: `admin123`

## License

MIT License
