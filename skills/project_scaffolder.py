def run(message):
    """
    Generate project structure boilerplate.
    Usage: scaffold <type> project
    """
    msg = message.lower()
    
    if "flask" in msg:
        return (
            "📂 **Flask Project Structure:**\n"
            "```text\n"
            "flask_app/\n"
            "├── app/\n"
            "│   ├── __init__.py       # App factory\n"
            "│   ├── routes.py         # Views\n"
            "│   ├── models.py         # Database models\n"
            "│   ├── templates/        # HTML files\n"
            "│   └── static/           # CSS/JS/Images\n"
            "├── config.py\n"
            "├── requirements.txt\n"
            "└── run.py                # Entry point\n"
            "```"
        )
    elif "python" in msg:
        return (
            "📂 **Python Project Structure:**\n"
            "```text\n"
            "project_root/\n"
            "├── venv/                 # Virtual environment\n"
            "├── src/                  # Source code\n"
            "│   ├── __init__.py\n"
            "│   └── main.py\n"
            "├── tests/                # Unit tests\n"
            "│   ├── __init__.py\n"
            "│   └── test_main.py\n"
            "├── requirements.txt      # Dependencies\n"
            "├── .gitignore\n"
            "└── README.md\n"
            "```\n"
            "💡 *Tip: Run `python -m venv venv` to start.*"
        )
    elif "node" in msg or "javascript" in msg:
        return (
            "📂 **Node.js Project Structure:**\n"
            "```text\n"
            "project_root/\n"
            "├── node_modules/         # Dependencies\n"
            "├── src/                  # Source code\n"
            "│   └── index.js\n"
            "├── tests/                # Tests\n"
            "├── package.json          # Config & Deps\n"
            "├── .gitignore\n"
            "└── README.md\n"
            "```\n"
            "💡 *Tip: Run `npm init -y` to generate package.json.*"
        )
    elif "react" in msg:
        return (
            "📂 **React Project Structure:**\n"
            "```text\n"
            "react_app/\n"
            "├── node_modules/\n"
            "├── public/\n"
            "│   └── index.html\n"
            "├── src/\n"
            "│   ├── components/       # Reusable components\n"
            "│   ├── App.js            # Main component\n"
            "│   ├── index.js          # Entry point\n"
            "│   └── App.css\n"
            "├── package.json\n"
            "└── README.md\n"
            "```\n"
            "💡 *Tip: Run `npx create-react-app .` to start.*"
        )
    
    return "Usage: scaffold <python|node|flask|react> project"

skill = {
    "name": "Project Scaffolder",
    "description": "Generates directory structures for common project types.",
    "triggers": ["scaffold project", "create project structure", "generate project"],
    "run": run
}