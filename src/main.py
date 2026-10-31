from config_descriptioin import *
from talk_helper import *
import os

def main():
    os.path.isfile("../config.json")
    config = AppConfig.from_json("../config.json" if os.path.isfile("../config.json") else "config.json")
    print(config)

    app = TalkHelperApp(config)

    app.mainloop()

if __name__ == "__main__":
    main()