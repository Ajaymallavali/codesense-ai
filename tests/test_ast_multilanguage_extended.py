import pytest
from conftest import TreeSitterScanner


def test_tree_sitter_available_languages():
    assert TreeSitterScanner.is_available()


def test_rust_ast_scanner():
    rust_code = """
    pub fn process_data(input: &str) -> Result<String, MyError> {
        unsafe {
            // Direct memory manipulation
            let raw_ptr = input.as_ptr();
        }
        let result = parse(input).unwrap();
        panic!("unexpected state");
        Ok(result)
    }
    """
    findings = TreeSitterScanner.scan_code("src/lib.rs", rust_code, ".rs")
    titles = [f["title"] for f in findings]
    
    assert any("Unsafe block detected" in t for t in titles)
    assert any("unwrap() call" in t for t in titles)
    assert any("panic!" in t for t in titles)


def test_c_cpp_ast_scanner():
    c_code = """
    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>

    void vulnerable(char *input) {
        char buffer[64];
        strcpy(buffer, input);
        system("ls -la");
        goto cleanup;
    cleanup:
        return;
    }
    """
    findings = TreeSitterScanner.scan_code("src/main.c", c_code, ".c")
    titles = [f["title"] for f in findings]

    assert any("strcpy" in t for t in titles)
    assert any("system()" in t for t in titles)
    assert any("goto" in t for t in titles)


def test_php_ast_scanner():
    php_code = """
    <?php
    function execute_dynamic($code) {
        eval($code);
        system("cat " . $_GET['file']);
        $hash = md5($code);
        $db->query("SELECT * FROM users WHERE name = '" . $_POST['username'] . "'");
    }
    """
    findings = TreeSitterScanner.scan_code("src/api.php", php_code, ".php")
    titles = [f["title"] for f in findings]

    assert any("eval()" in t for t in titles)
    assert any("command injection" in t.lower() or "system" in t.lower() for t in titles)
    assert any("Weak hashing" in t or "md5" in t for t in titles)
