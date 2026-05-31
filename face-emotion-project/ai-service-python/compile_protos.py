import os
import sys

def compile_proto():
    # Configure UTF-8 encoding for stdout on Windows to prevent UnicodeEncodeError
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    # Ensure generated directory exists
    os.makedirs("generated", exist_ok=True)
    
    # Create empty __init__.py in generated
    with open(os.path.join("generated", "__init__.py"), "w") as f:
        pass
        
    try:
        from grpc_tools import protoc
    except ImportError:
        print("[!] Missing 'grpcio-tools' library.")
        print("[*] Please run: pip install grpcio-tools")
        return False

    print("[*] Compiling protobuf file 'emotion.proto'...")
    
    # Run protoc compilation
    status = protoc.main((
        '',
        '-I.',
        '--python_out=.',
        '--grpc_python_out=.',
        'protos/emotion.proto',
    ))

    if status == 0:
        print("[+] Protobuf compilation successful!")
        
        import shutil
        for name in ["emotion_pb2.py", "emotion_pb2_grpc.py"]:
            src = os.path.join("protos", name)
            dst = os.path.join("generated", name)
            if os.path.exists(src):
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(src, dst)
                
        # Fix relative imports in generated/emotion_pb2_grpc.py
        grpc_path = os.path.join("generated", "emotion_pb2_grpc.py")
        if os.path.exists(grpc_path):
            with open(grpc_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Replace import styles
            content = content.replace(
                "import protos.emotion_pb2 as", 
                "import generated.emotion_pb2 as"
            )
            content = content.replace(
                "from protos import emotion_pb2 as", 
                "from generated import emotion_pb2 as"
            )
            
            with open(grpc_path, 'w', encoding='utf-8') as file:
                file.write(content)
                
            print("[+] Successfully moved and updated Python gRPC files in 'generated/'!")
        return True
    else:
        print(f"[-] Protobuf compilation failed with exit code: {status}")
        return False

if __name__ == "__main__":
    compile_proto()
