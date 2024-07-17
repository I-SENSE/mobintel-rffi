import os
from dotenv import load_dotenv
from openai import OpenAI
from threading import Lock

load_dotenv()

class OpenAIClient:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OpenAIClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # Avoid re-initialization
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.initialized = True

    def extract_info_from_output(self, prompt, model="gpt-4o"):    
        response = self.client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": prompt
                    }
                ]
                }],
            temperature=1,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response.choices[0].message.content.strip()

    def prompt_is_ls_successful(self, stdoutput):
        prompt = f"""
            I just ran a command 'ls /root/' on a remote server. My goal is to check whether the server booted or it's still unavailable. 

            Here's the response for the command: 
            {stdoutput}

            If the ls response was successful -- reply YES. If not -- reply NO. Use only YES or NO in your answer.
            """
        
        response = self.extract_info_from_output(prompt)
        print(f"OpenAI says: {response}")

        if response == 'YES':
            return True
        elif response == 'NO':
            return False
        else: 
            print(f"Unexpected LLM response: {response}")
            return False
        
    def prompt_find_usrp_interface(self, stdoutput):
        prompt = f"""
            I'm running a command 'ifconfig' on my system: 

            I need to configure connection to a USRP from an Ubuntu instance, connected via Ethernet. 
            The documentation says "For USRP2s (and N210s), the Ethernet interface of each device is connected to 
            a (third) dedicated Ethernet interface on the node that is used solely for USRP related communication."

            Here's 'ifconfig' output:

            {stdoutput}

            The documentation says "The documentation says "For USRP2s (and N210s), the Ethernet interface of each device is connected to a (third) dedicated Ethernet interface on the node that is used solely for USRP related communication". 

            Which interface I should be using? Provide only the name of the interface. If nothing available -- reply NONE.
            """

        response = self.extract_info_from_output(prompt)
        print(f"OpenAI says: {response}")
        return response

    def prompt_find_wifi_interface(self, stdoutput):
        prompt = f"""
            I'm running a command 'iwconfig' on my system. Here's its output:

            {stdoutput}

            I need to identify the WiFi interface (Atheros) that I should configure.

            Which interface I should be using? Provide only the name of the interface. If nothing available -- reply NONE.
            """

        response = self.extract_info_from_output(prompt)
        print(f"OpenAI says: {response}")
        return response