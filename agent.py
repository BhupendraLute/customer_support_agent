from google.adk import Agent, Context, Workflow
from google.adk.workflow import node, RetryConfig

# Retry configuration for handling transient API errors (e.g. 503 Service Unavailable, 429 Rate Limits)
transient_retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=10.0,
    backoff_factor=2.0,
    jitter=1.0
)

classifier_agent = Agent(
    model='gemini-2.5-flash',
    name='classifier_agent',
    retry_config=transient_retry_config,
    instruction=(
        'You are an AI assistant that classifies user customer service queries.\n'
        'Determine if the user query is related to shipping (rates, tracking, delivery, returns) '
        'or unrelated to shipping.\n'
        'If the query is related to shipping, respond with: shipping\n'
        'If the query is unrelated, respond with: unrelated\n'
        'Respond with ONLY "shipping" or "unrelated" and nothing else.'
    )
)

shipping_faq_agent = Agent(
    model='gemini-2.5-flash',
    name='shipping_faq_agent',
    description='Answers shipping questions.',
    retry_config=transient_retry_config,
    instruction=(
        'You are a customer support agent for a shipping company.\n'
        'Answer the user\'s shipping-related questions (about rates, tracking, delivery, returns) '
        'politely, accurately, and professionally.'
    )
)

decline_agent = Agent(
    model='gemini-2.5-flash',
    name='decline_agent',
    description='Declines to answer unrelated questions.',
    retry_config=transient_retry_config,
    instruction=(
        'You are a customer support agent for a shipping company.\n'
        'The user has asked a question that is unrelated to shipping.\n'
        'Politely decline to answer their query, explaining that you can only assist with '
        'shipping-related inquiries (rates, tracking, delivery, returns).'
    )
)

@node(name='classifier_node', rerun_on_resume=True, retry_config=transient_retry_config)
async def classifier_node(ctx: Context, node_input: str) -> str:
    # Run the classifier agent to classify the user query
    result = await ctx.run_node(classifier_agent, node_input=node_input)
    classification = result.strip().lower()
    
    if 'shipping' in classification:
        ctx.route = 'shipping'
    else:
        ctx.route = 'unrelated'
        
    return node_input

root_agent = Workflow(
    name='root_agent',
    description='Customer support agent that routes shipping-related queries to FAQ and declines unrelated ones.',
    edges=[
        ('START', classifier_node),
        (classifier_node, {
            'shipping': shipping_faq_agent,
            'unrelated': decline_agent
        })
    ]
)


