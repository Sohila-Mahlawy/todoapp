from openai import OpenAI

# Initialize the DeepSeek API client
client = OpenAI(api_key="sk-6893bfcc17c640ec8c89de05ac8e2c7b", base_url="https://api.deepseek.com")
# Home page with form
def api(request):
    if request.method == "POST":
        # Get form data
        project_name = request.form.get("project_name")
        project_description = request.form.get("project_description")
        employees = request.form.get("employees")

        # Detect if the input is in Arabic
        is_arabic = any("\u0600" <= char <= "\u06FF" for char in project_name + project_description + employees)

        # Generate prompt for the model
        prompt = f"""
        Project Name: {project_name}
        Project Description: {project_description}

        Employees:
        {employees}

        Break this project into smaller tasks with descriptions. Then, assign each task to the most suitable employee based on their skills and position. Provide a reason for each assignment.
        """

        # Add language instruction to the prompt
        if is_arabic:
            prompt += "\n\nPlease respond in Arabic."

        # Send prompt to DeepSeek API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a project management assistant."},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )

        # Get the generated tasks, assignments, and reasons
        tasks_and_assignments = response.choices[0].message.content

        # Render results page
        return render(request, "result.html", tasks_and_assignments=tasks_and_assignments)

    # Render form page
    return render(request, "index.html")