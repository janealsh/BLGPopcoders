from flask import Flask, render_template
app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>Welcome To Popcoders Project</h1>"

@app.route("/reviews")
def reviews():
    return render_template("reviews.html")

@app.route("/watch_history")
def watch_history():
    return render_template("watch_history.html")

@app.route("/recommend")
def recommend():
    return render_template("recommend.html")

if __name__ == '__main__':
    app.run(host="0.0.0.0" , port=8080 , debug=True)
