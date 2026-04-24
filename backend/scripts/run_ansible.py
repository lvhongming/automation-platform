#!/usr/bin/env python3
"""
Ansible 执行测试脚本
用于测试 Ansible 命令是否可用
"""
import subprocess
import sys


def run_command(cmd):
    """运行命令并返回结果"""
    print(f"执行命令: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"返回码: {result.returncode}")
        if result.stdout:
            print(f"标准输出:\\n{result.stdout}")
        if result.stderr:
            print(f"标准错误:\\n{result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("命令执行超时")
        return False
    except Exception as e:
        print(f"执行错误: {e}")
        return False


def main():
    print("=" * 50)
    print("Ansible 环境检查")
    print("=" * 50)

    checks = []

    # 检查 ansible 命令
    print("\\n[1] 检查 ansible 命令...")
    checks.append(("ansible", run_command(["ansible", "--version"])))

    # 检查 ansible-playbook 命令
    print("\\n[2] 检查 ansible-playbook 命令...")
    checks.append(("ansible-playbook", run_command(["ansible-playbook", "--version"])))

    # 检查 ansible-galaxy 命令
    print("\\n[3] 检查 ansible-galaxy 命令...")
    checks.append(("ansible-galaxy", run_command(["ansible-galaxy", "--version"])))

    # 检查 ansible 配置
    print("\\n[4] 检查 ansible 配置文件...")
    checks.append(("ansible.cfg", run_command(["ansible", "--version", "|", "head", "-1"])))

    # 检查 Python ansible 模块
    print("\\n[5] 检查 Python ansible 模块...")
    try:
        import ansible
        print(f"ansible 模块版本: {ansible.__version__}")
        checks.append(("ansible module", True))
    except ImportError:
        print("ansible 模块未安装")
        checks.append(("ansible module", False))

    # 检查 ansible-runner
    print("\\n[6] 检查 ansible-runner...")
    try:
        import ansible_runner
        print(f"ansible-runner 版本: {ansible_runner.__version__}")
        checks.append(("ansible-runner", True))
    except ImportError:
        print("ansible-runner 未安装")
        checks.append(("ansible-runner", False))

    # 总结
    print("\\n" + "=" * 50)
    print("检查结果汇总")
    print("=" * 50)
    for name, passed in checks:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")

    all_passed = all(passed for _, passed in checks)
    print("\\n总体状态:", "全部通过" if all_passed else "存在问题")
    print("=" * 50)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
