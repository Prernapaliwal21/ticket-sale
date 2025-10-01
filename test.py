from flask import Flask, render_template_string, request

app = Flask(__name__)

@app.route("/pay")
def pay():
    amount = request.args.get("amount", "100")
    order_id = "ORDER12345"
    upi_id = "manansharma0621@okicici"
    payee = "Prerna"

    upi_link = (
        f"upi://pay?pa={upi_id}&pn={payee}&am={amount}&cu=INR&tr={order_id}&tn=Payment%20for%20{order_id}"
    )

    return render_template_string(
        """
        <h2>Pay with Google Pay</h2>
        <a href="{{ upi_link }}">
          <img src="https://upload.wikimedia.org/wikipedia/commons/5/5a/Google_Pay_Logo.svg" width="150">
        </a>
        """,
        upi_link=upi_link
    )

if __name__ == "__main__":
    app.run(debug=True)
