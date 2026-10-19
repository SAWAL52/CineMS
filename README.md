# CineMS — Cinema Booking System

CineMS is a web-based cinema booking system built with Django and Python. It provides a platform where users can explore movies, view available showtimes, select seats, and manage their reservations through a simple web interface.

The system also includes cinema and hall management, user authentication, and PayBridgeNP payment integration.

## Features

### User Features
- Browse available movies and view movie details.
- Explore cinema showtimes.
- View available and reserved seats.
- Select seats for a particular show.
- Reserve seats and manage booking status.
- Make payments through the integrated PayBridgeNP payment gateway.
- View personal booking history.
- Register, log in, log out, and manage user profiles.

### Administration Features
- Manage movies and movie posters.
- Manage cinemas and cinema halls.
- Manage shows, showtimes, and ticket prices.
- Manage seats and reservations.
- Monitor booking information through the Django administration interface.

### Technical Features
- Django-based backend and database models.
- Django ORM for database operations.
- Django authentication and session management.
- Server-rendered HTML templates.
- Tailwind CSS for responsive styling.
- Payment return and cancellation handling.
- Reservation status management and seat-conflict prevention.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Django | Web framework |
| SQLite | Development database |
| HTML5 | Page structure |
| Tailwind CSS | User interface styling |
| JavaScript | Client-side interactions |
| PayBridgeNP | Payment gateway integration |

## Project Structure

```text
django_cinema/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── core/
│   ├── migrations/
│   ├── management/
│   ├── templates/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── media/
│   └── movie_posters/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

*Note: The structure above is illustrative. Adjust it to match the actual files and directories in your repository.*

## Getting Started

Follow these instructions to run CineMS locally.

### 1. Prerequisites

Install the following:

- Python 3.12 or a compatible version supported by your installed Django release.
- Git.
- A web browser.

### 2. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

Replace the repository URL with your actual GitHub repository URL.

### 3. Create a Virtual Environment

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks virtual-environment activation, consult the official Python documentation or use the appropriate activation method for your shell.

### 4. Install Dependencies

Upgrade pip and install the project dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `requirements.txt` does not exist yet, create it from your working environment:

```powershell
python -m pip freeze > requirements.txt
```

Review the generated file and remove unrelated packages where appropriate.

### 5. Configure Environment Variables

Create a local `.env` file using `.env.example` as a reference, if your project uses environment variables.

Configure the required settings, such as:

- Django secret key.
- Debug mode.
- Allowed hosts.
- PayBridgeNP merchant credentials and other required gateway settings.

Use placeholder values in `.env.example`. Never commit real credentials or production secrets to GitHub.

Make sure your Django settings actually load these environment variables using your chosen configuration method.

### 6. Apply Database Migrations

Create the database tables:

```powershell
python manage.py migrate
```

If model changes have not yet been migrated, first run:

```powershell
python manage.py makemigrations
python manage.py migrate
```

Commit the required migration files to GitHub so other developers can reproduce the database schema.

### 7. Create an Administrator Account

To access the Django administration interface:

```powershell
python manage.py createsuperuser
```

Follow the prompts to configure your administrator account.

### 8. Load Demo Data (Optional)

If the project includes a demo-data management command, run:

```powershell
python manage.py seed_demo
```

This command is optional and should be included in the instructions only after the command has been implemented and tested.

Alternatively, add movies, cinemas, halls, seats, and showtimes through the Django administration interface.

### 9. Run the Development Server

```powershell
python manage.py runserver
```

Open the application in your browser:

- **Website:** http://127.0.0.1:8000/
- **Admin panel:** http://127.0.0.1:8000/admin/

The default Django development server is intended for local development, not production deployment.

## Payment Integration

CineMS integrates with PayBridgeNP to support the payment workflow associated with seat reservations.

The integration includes payment initiation and handling of payment return and cancellation flows.

To test the integration:

1. Configure the payment gateway settings required by your implementation.
2. Use the gateway's authorized test environment, if available.
3. Initiate a booking and follow the payment flow.
4. Verify the return and cancellation behavior.
5. Confirm the reservation status and seat availability after each outcome.

Payment success should be determined by the verification mechanism required by the gateway, not solely by a browser redirect. Use the gateway's documented verification and callback procedures before relying on the integration in production.

Do not publish merchant secrets, API credentials, private keys, or real customer payment data.

## Reservation Workflow

The general booking workflow is:

1. The user browses movies.
2. The user selects a showtime.
3. The system displays the seats associated with the selected show.
4. The user selects available seats.
5. The system creates and manages the reservation.
6. The user proceeds through the configured payment process.
7. The system handles the payment result and updates the reservation according to the implemented workflow.
8. The user can review their bookings.

The application uses reservation statuses to represent booking states. The precise status transitions and any reservation-expiration behavior depend on the implementation and configuration.

## Database Design

The main entities in the system include:

- **Movie:** Movie information and poster.
- **Cinema:** Cinema name and location.
- **CinemaHall:** A hall associated with a cinema.
- **Show:** Movie screening, showtime, hall, and ticket price.
- **Seat:** A seat belonging to a cinema hall.
- **Reservation:** Customer, show, seat, and reservation status.

The database relationships connect movies to shows, cinemas to halls, halls to seats, and customers to their reservations.

The project also uses database constraints to help prevent the same seat from being reserved more than once for the same show.

## Development Checks

Before committing changes, run:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The test command runs the project's configured Django tests. Add tests for authentication, seat availability, reservation conflicts, payment outcomes, and cancellation behavior as appropriate.

## Security and Deployment Notes

Before deploying CineMS:

- Set `DEBUG = False`.
- Use a strong, private Django secret key.
- Configure `ALLOWED_HOSTS` appropriately.
- Use HTTPS.
- Store credentials in environment variables or a secure secrets manager.
- Configure a production-ready database and web server.
- Review authentication, authorization, and CSRF protection.
- Verify payment results using the gateway's documented procedures.
- Protect user, booking, and payment-related data.
- Configure backups and logging.
- Serve static and uploaded media files appropriately.
- Review reservation concurrency and expiration behavior.

Do not use Django's development server as a production server.

## Contributing

Contributions and suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement your changes.
4. Test the application.
5. Submit a pull request with a description of the changes.

## License

No license has been specified yet.

If you intend to allow others to reuse, modify, or distribute this project, choose an appropriate open-source license and add its license file to the repository.

## Acknowledgements

- Django for the web framework.
- Tailwind CSS for interface styling.
- PayBridgeNP for payment integration.
- The open-source community for its tools and documentation.

---

**CineMS — Discover movies. Choose your seats. Enjoy the show.**
