-- Neptune Pool Payouts - Database Schema
-- Fixed record_payout_batch to update payouts.status to 'paid'

CREATE OR REPLACE FUNCTION record_payout_batch(
    p_payment_ids BIGINT[],
    p_transaction_hash VARCHAR(128),
    p_fee NUMERIC(20,8)
) RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_batch_id BIGINT;
    v_total_amount NUMERIC(20,8);
    v_recipients_count INTEGER;
    v_payouts_updated INT;
BEGIN
    SELECT 
        SUM(amount),
        COUNT(DISTINCT miner_address)
    INTO v_total_amount, v_recipients_count
    FROM payments
    WHERE id = ANY(p_payment_ids);
    
    INSERT INTO payout_batches (payment_ids, transaction_hash, recipients_count, total_amount, fee, command_text, status, executed_at)
    VALUES (p_payment_ids, p_transaction_hash, v_recipients_count, v_total_amount, p_fee, 'neptune-cli send-to-many', 'completed', NOW())
    RETURNING id INTO v_batch_id;
    
    UPDATE payments
    SET status = 'completed', transaction_hash = p_transaction_hash, processed_at = NOW(), confirmed_at = NOW(),
        payment_batch_id = (SELECT batch_uuid FROM payout_batches WHERE id = v_batch_id)
    WHERE id = ANY(p_payment_ids);
    
    UPDATE payouts
    SET status = 'paid', paid_at = NOW(),
        metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{paid_tx_hash}', to_jsonb(p_transaction_hash))
    WHERE payment_id = ANY(p_payment_ids);
    
    GET DIAGNOSTICS v_payouts_updated = ROW_COUNT;
    
    RETURN v_batch_id;
END;
$$;
