"""测试 nexus_vpn.core.system 模块"""
import pytest
from unittest.mock import patch, MagicMock


class TestSystemChecker:
    """SystemChecker 类测试"""
    
    def test_system_checker_import(self):
        """测试 SystemChecker 可以正常导入"""
        from nexus_vpn.core.system import SystemChecker
        assert SystemChecker is not None
    
    def test_check_os_linux_with_apt(self, mocker):
        """测试 Linux 系统且有 apt-get"""
        mocker.patch('platform.system', return_value='Linux')
        mocker.patch('shutil.which', return_value='/usr/bin/apt-get')
        
        from nexus_vpn.core.system import SystemChecker
        # 不应该抛出异常或退出
        try:
            SystemChecker.check_os()
        except SystemExit:
            pytest.fail("check_os() 不应该在 Linux + apt-get 环境下退出")
    
    def test_check_os_linux_with_yum(self, mocker):
        """测试 Linux 系统且有 yum"""
        mocker.patch('platform.system', return_value='Linux')
        # apt-get 不存在，但 yum 存在
        def which_side_effect(cmd):
            if cmd == 'apt-get':
                return None
            elif cmd == 'yum':
                return '/usr/bin/yum'
            return None
        mocker.patch('shutil.which', side_effect=which_side_effect)
        
        from nexus_vpn.core.system import SystemChecker
        try:
            SystemChecker.check_os()
        except SystemExit:
            pytest.fail("check_os() 不应该在 Linux + yum 环境下退出")
    
    def test_check_os_non_linux(self, mocker):
        """测试非 Linux 系统应该退出"""
        mocker.patch('platform.system', return_value='Darwin')
        
        from nexus_vpn.core.system import SystemChecker
        with pytest.raises(SystemExit) as exc_info:
            SystemChecker.check_os()
        assert exc_info.value.code == 1
    
    def test_check_os_linux_no_package_manager(self, mocker):
        """测试 Linux 但没有包管理器应该退出"""
        mocker.patch('platform.system', return_value='Linux')
        mocker.patch('shutil.which', return_value=None)
        
        from nexus_vpn.core.system import SystemChecker
        with pytest.raises(SystemExit) as exc_info:
            SystemChecker.check_os()
        assert exc_info.value.code == 1
