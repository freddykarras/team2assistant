from flask import Flask, render_template_string, request, jsonify
from main import run_pipeline, load_faculty_database

app = Flask(__name__)
records = load_faculty_database()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>VTURCS Team 2 Assistant</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 min-h-screen p-8 text-slate-800">
    <div class="max-w-4xl mx-auto bg-white rounded-xl shadow-md p-6 border border-slate-200">
        <h1 class="text-2xl font-bold text-maroon-800 text-amber-900 mb-2">VTURCS AI Research Assistant</h1>
        <p class="text-sm text-slate-500 mb-6">Team 2 Prototype • Decision Support & Faculty Outreach Generator</p>
        
        <form method="POST" action="/search" class="space-y-4">
            <div>
                <label class="block text-sm font-semibold mb-1">Research Description / Project Interests:</label>
                <textarea name="text" rows="3" class="w-full p-3 border rounded-lg focus:ring-2 focus:ring-amber-700 outline-none" placeholder="e.g., I built a web vulnerability scanner in CS 4264 and know Python..."></textarea>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-semibold mb-1">Experience Tier:</label>
                    <select name="tier" class="w-full p-2 border rounded-lg">
                        <option value="Novice">Novice</option>
                        <option value="Intermediate" selected>Intermediate</option>
                        <option value="Experienced">Experienced</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-semibold mb-1">Condition:</label>
                    <select name="condition" class="w-full p-2 border rounded-lg">
                        <option value="B" selected>Condition B (Scaffolded Guidance)</option>
                        <option value="A">Condition A (Direct Answer)</option>
                        <option value="both">Both</option>
                    </select>
                </div>
            </div>
            
            <button type="submit" class="w-full bg-amber-800 hover:bg-amber-900 text-white font-semibold py-2 px-4 rounded-lg transition">
                Find Matching Faculty & Generate Guidance
            </button>
        </form>

        {% if result %}
        <hr class="my-6">
        <div class="space-y-4">
            <h2 class="text-lg font-bold text-slate-900">Search Output</h2>
            <div class="p-3 bg-slate-100 rounded-lg text-sm">
                <strong>Extracted Research Tags:</strong> {{ result.tags | join(', ') if result.tags else 'None' }}
            </div>
            
            <h3 class="font-semibold text-md">Supported Faculty Matches:</h3>
            <div class="space-y-2">
                {% for item in result.matches %}
                <div class="p-3 border rounded-lg bg-slate-50 flex justify-between items-center">
                    <div>
                        <span class="font-bold text-amber-900">{{ item.faculty.name }}</span> 
                        <span class="text-xs text-slate-500">({{ item.faculty.id }})</span>
                        <div class="text-xs text-slate-600">{{ item.faculty.research_area }}</div>
                    </div>
                    <span class="bg-amber-100 text-amber-900 font-bold text-xs px-2 py-1 rounded">
                        Score: {{ item.score }}
                    </span>
                </div>
                {% endfor %}
            </div>

            {% if result.guidance %}
            <h3 class="font-semibold text-md mt-4">Generated Guidance Output:</h3>
            {% for cond, text in result.guidance.items() %}
            <pre class="p-4 bg-slate-900 text-slate-100 text-xs rounded-lg whitespace-pre-wrap font-mono">{{ text }}</pre>
            {% endfor %}
            {% endif %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/search", methods=["POST"])
def search():
    text = request.form.get("text", "")
    tier = request.form.get("tier", "Intermediate")
    condition = request.form.get("condition", "B")
    
    result = None
    if text.strip():
        try:
            result = run_pipeline(text, tier, condition, records)
        except Exception as e:
            result = {"error": str(e)}
            
    return render_template_string(HTML_TEMPLATE, result=result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)