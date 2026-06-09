from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
from planet_gen import generate_planet_textures

app = Flask(__name__)
CORS(app)

TEXTURE_DIR = os.path.join(os.path.dirname(__file__), "static", "textures")
os.makedirs(TEXTURE_DIR, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/planet", methods=["POST"])
def planet():
    """
    Accept planet parameters, generate textures server-side,
    return URLs the frontend can load into Three.js.
    """
    params = request.get_json(force=True)
    if not params:
        return jsonify({"error": "No parameters supplied"}), 400

    try:
        result = generate_planet_textures(params, TEXTURE_DIR)
        return jsonify(result)
    except Exception as e:
        print(f"Generation error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/static/textures/<path:filename>")
def textures(filename):
    return send_from_directory(TEXTURE_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
