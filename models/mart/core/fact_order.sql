with payments as (

select * from {{ source('stripe','payment') }}
),
orders as (
    select * from {{ref('stg_orders')}}
),
final_order as (
select  orders.order_id as order_id,
        orders.customer_id as customer_id,
        payments.AMOUNT  
from orders left join payments on payments.orderid=orders.order_id 

)
Select * from final_order