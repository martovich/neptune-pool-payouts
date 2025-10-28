#!/usr/bin/env python3
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, jsonify
import subprocess
import json
from datetime import datetime

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': '172.16.0.180',
    'port': 5432,
    'database': 'neptune_pool',
    'user': 'neptune_pool',
    'password': 'neptune_pool_secure_2025'
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/pending-payments')
def get_pending_payments():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Получаем агрегированные платежи
        cur.execute('''
            SELECT 
                miner_address,
                payments_count,
                total_amount,
                oldest_payment,
                newest_payment,
                payment_ids
            FROM pending_payments_grouped
            ORDER BY total_amount DESC
        ''')
        
        payments = cur.fetchall()
        
        # Форматируем для JSON
        result = []
        for p in payments:
            result.append({
                'address': p['miner_address'],
                'count': p['payments_count'],
                'amount': float(p['total_amount']),
                'oldest': p['oldest_payment'].isoformat() if p['oldest_payment'] else None,
                'newest': p['newest_payment'].isoformat() if p['newest_payment'] else None,
                'payment_ids': p['payment_ids']
            })
        
        cur.close()
        conn.close()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-command', methods=['POST'])
def generate_command():
    try:
        data = request.json
        recipients = data.get('recipients', [])
        fee = data.get('fee', 0.001)
        
        # Формируем строку получателей address:amount
        outputs = []
        for r in recipients:
            outputs.append(f"{r['address']}:{r['amount']}")
        
        # Формируем команду
        command = f"neptune-cli send-to-many --fee {fee} {' '.join(outputs)}"
        
        return jsonify({
            'command': command,
            'recipients_count': len(recipients),
            'total_amount': sum(r['amount'] for r in recipients)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/execute-payout', methods=['POST'])
def execute_payout():
    try:
        data = request.json
        command = data.get('command')
        payment_ids = data.get('payment_ids', [])
        fee = data.get('fee', 0.001)
        
        # Выполняем команду neptune-cli
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': result.stderr or 'Command failed'
            }), 400
        
        # Парсим вывод чтобы получить transaction hash
        # Предполагаем что neptune-cli возвращает хеш транзакции
        output = result.stdout.strip()
        tx_hash = output  # Нужно будет адаптировать под реальный формат вывода
        
        # Записываем в БД
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute(
            'SELECT record_payout_batch(%s, %s, %s)',
            (payment_ids, tx_hash, fee)
        )
        
        batch_id = cur.fetchone()[0]
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'tx_hash': tx_hash,
            'batch_id': batch_id
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Command timeout'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/payout-history')
def payout_history():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute('''
            SELECT 
                id,
                batch_uuid,
                transaction_hash,
                recipients_count,
                total_amount,
                fee,
                status,
                created_at,
                executed_at
            FROM payout_batches
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        
        batches = cur.fetchall()
        
        result = []
        for b in batches:
            result.append({
                'id': b['id'],
                'uuid': str(b['batch_uuid']),
                'tx_hash': b['transaction_hash'],
                'recipients': b['recipients_count'],
                'amount': float(b['total_amount']),
                'fee': float(b['fee']),
                'status': b['status'],
                'created': b['created_at'].isoformat() if b['created_at'] else None,
                'executed': b['executed_at'].isoformat() if b['executed_at'] else None
            })
        
        cur.close()
        conn.close()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Слушаем только на локальном интерфейсе
    app.run(host='172.16.0.180', port=5001, debug=False)
