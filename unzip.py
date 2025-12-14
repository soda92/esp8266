import ustruct
import uos

def extract(zip_path, dest_dir):
    with open(zip_path, 'rb') as f:
        while True:
            # Read Local File Header Signature
            sig = f.read(4)
            if sig != b'PK\x03\x04':
                break # End of Central Directory
            
            # Skip version (2), flags (2)
            f.read(4)
            # Compression method
            method = ustruct.unpack('<H', f.read(2))[0]
            # Time/Date (4), CRC (4)
            f.read(8)
            # Sizes
            comp_size, uncomp_size = ustruct.unpack('<II', f.read(8))
            name_len, extra_len = ustruct.unpack('<HH', f.read(4))
            
            filename = f.read(name_len).decode('utf-8')
            f.read(extra_len)
            
            print(f"Extracting {filename}...")
            
            # Prepare path
            out_path = dest_dir + filename
            
            # Directory?
            if filename.endswith('/'):
                try: uos.mkdir(out_path)
                except: pass
                continue
                
            # Read Data
            data = f.read(comp_size)
            
            if method == 0:
                # Store (No compression)
                pass
            elif method == 8:
                # Deflate
                try:
                    import uzlib
                    data = uzlib.decompress(data, -15)
                except ImportError:
                    print("Error: uzlib not found. Use ZIP_STORED.")
                    continue
                except Exception as e:
                    print(f"Decompression error: {e}")
                    continue
            else:
                print(f"Unknown compression method: {method}")
                continue
            
            with open(out_path, 'wb') as out_f:
                out_f.write(data)
