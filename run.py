from llm import AliceLLM

alice = AliceLLM()

while True:
    question = input("You: ")

    if question.lower() == "exit":
        break

    response = alice.ask(question)

    print("ALICE:", response)