with customers as (

   select * from {{ref('stg_customer')}}

),

orders as (

    select * from {{ref('stg_orders')}}

),

customer_orders as (

    select
        customer_id,

        min(order_date) as first_order_date,
        max(order_date) as most_recent_order_date,
        count(order_id) as number_of_orders

    from orders

    group by customer_id

),

fact_orders as (
    select customer_id,sum(AMOUNT) as lifetime_value  from {{ref('fact_order')}}
    group by ALL
),

final as (

    select
        customers.customer_id,
        customers.first_name,
        customers.last_name,
        customer_orders.first_order_date,
        customer_orders.most_recent_order_date,
        coalesce(customer_orders.number_of_orders, 0) as number_of_orders,
        coalesce(fact_orders.lifetime_value,0) as lifetime_value
    from customers

    left join customer_orders using (customer_id)
    left join fact_orders using (customer_id)
)

select * from final