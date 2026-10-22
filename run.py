from llm import AliceLLM

alice = AliceLLM()

# CHANGE: history list add ki.
# WHY:    pehle har sawaal naya hota tha, to terminal mein "memory" test nahi ho paati thi
#         (jabki browser version history bhejta hai).
history = []

while True:
    question = input("You: ").strip()
    if question.lower() == "exit":
        break
    if not question:
        continue

    response = alice.ask(question, history)
    print("ALICE:", response)

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": response})