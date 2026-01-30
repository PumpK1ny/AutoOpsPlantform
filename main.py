from AI.news_collector import NewsCollector
from AI.fund_analysiser import FundAnalysiser

if __name__ == "__main__":

    ai = NewsCollector()
    while True:
        user_input = input("\n\n用户: ")
        if user_input.lower() == "exit":
            break
        response = ai.run(user_input)
