#ifndef ase_lib_h_
#define ase_lib_h_

char* encrypt(const char* plain_text);
char* decrypt(const char* b64_str);
void setKey(const char* key);
void setIV(const char* iv);

#endif