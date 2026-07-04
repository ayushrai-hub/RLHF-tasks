import subprocess
import re

while True:
    print("Running docker build...")
    result = subprocess.run(["docker", "build", ".", "-t", "testbuild"], capture_output=True, text=True)
    if result.returncode == 0:
        print("Build succeeded!")
        break
    
    output = result.stderr + "\n" + result.stdout
    
    # Example error:
    # Expected sha256 bcbd7be9ba2fc81ee85e78749fc1a11579294f99ddbf3a0026e649ba38bc93a9
    # Expected     or d5cb21ab79116345ec4da2019b88dbb4c810ebc9167197472093e0984920b7d3
    #      Got        3111b9d131c238bec2f8f516e123e14ba243563fb135d3fe885990585aa7795b
    
    match = re.search(r"Expected sha256 ([a-f0-9]+).*?Got\s+([a-f0-9]+)", output, re.DOTALL)
    if not match:
        print("Could not find hash mismatch!")
        print(output)
        break
        
    expected1 = match.group(1)
    got = match.group(2)
    
    # Try to find expected2
    expected2 = None
    m2 = re.search(r"Expected\s+or\s+([a-f0-9]+)", output)
    if m2:
        expected2 = m2.group(1)
        
    with open("requirements.txt", "r") as f:
        content = f.read()
        
    if expected1 in content:
        print(f"Replacing {expected1} with {got}")
        content = content.replace(expected1, got)
    elif expected2 and expected2 in content:
        print(f"Replacing {expected2} with {got}")
        content = content.replace(expected2, got)
    else:
        print(f"Could not find {expected1} or {expected2} in requirements.txt!")
        break
        
    with open("requirements.txt", "w") as f:
        f.write(content)
