SELECT product_id FROM {{ ref('fct_order_items') }}
WHERE product_id IS NOT NULL GROUP BY product_id
