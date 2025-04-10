from flask import Flask, request, jsonify
import stripe

app = Flask(__name__)

# Your real Stripe Secret Key
stripe.api_key = 'sk_test_51RCBFoFKBqAW7XVSQmGtMJxYdp29lin7iacvFpAGs9JirJfmo3VkAzZh9JRnbLwmc8hL9FB61LiQS7nTWAIvn53e005e2sd1tY'

YOUR_DOMAIN = 'https://classy-shortbread-d08b8b.netlify.app'

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': 'price_1RCBWoFKBqAW7XVSCzUsX5ja',
                'quantity': 1,
            }],
            subscription_data={
                'trial_period_days': 7,
            },
            success_url=YOUR_DOMAIN + '/success.html',
            cancel_url=YOUR_DOMAIN + '/cancel.html',
        )
        return jsonify({'url': session.url})
    except Exception as e:
        return jsonify(error=str(e)), 400

if __name__ == '__main__':
    app.run(port=4242)
