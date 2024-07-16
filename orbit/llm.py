import subprocess
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
  api_key=os.getenv("OPENAI_API_KEY")
)

def extract_info_from_output(prompt, model="gpt-4o"):    
    response = client.chat.completions.create(
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

    return response.choices[0].message.content

def prompt_is_ls_successful(stdoutput):
    prompt = f"""
        I just ran a command 'ls /root/' on a remote server. My goal is to check whether the server booted or it's still unavailable. 

        Here's the response for the command: 
        {stdoutput}

        If the ls response was successful -- reply YES. If not -- reply NO. Use only YES or NO in your answer.
        """
    
    response = extract_info_from_output(prompt)
    print(f"OpenAI says: {response}")

    if response == 'YES':
        return True
    elif response == 'NO':
        return False
    else: 
        print(f"Unexpected LLM response: {response}")
        return False
    
def prompt_find_usrp_interface(stdoutput):
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

    response = extract_info_from_output(prompt)
    print(f"OpenAI says: {response}")
    return response

    
    
