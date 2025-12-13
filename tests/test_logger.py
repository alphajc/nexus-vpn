"""测试 nexus_vpn.utils.logger 模块"""
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock


class TestLogger:
    """Logger 类测试"""
    
    def test_logger_import(self):
        """测试 Logger 可以正常导入"""
        from nexus_vpn.utils.logger import Logger, log, console
        assert Logger is not None
        assert log is not None
        assert console is not None
    
    def test_custom_theme_defined(self):
        """测试自定义主题已定义"""
        from nexus_vpn.utils.logger import custom_theme
        assert custom_theme is not None
        # 验证主题包含预期的样式
        assert "info" in custom_theme.styles
        assert "warning" in custom_theme.styles
        assert "error" in custom_theme.styles
        assert "success" in custom_theme.styles
        assert "cmd" in custom_theme.styles
    
    def test_logger_info(self, mocker):
        """测试 info 方法"""
        from nexus_vpn.utils.logger import Logger, console
        mock_print = mocker.patch.object(console, 'print')
        Logger.info("测试信息")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "测试信息" in call_args
        assert "[info]" in call_args
    
    def test_logger_success(self, mocker):
        """测试 success 方法"""
        from nexus_vpn.utils.logger import Logger, console
        mock_print = mocker.patch.object(console, 'print')
        Logger.success("成功信息")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "成功信息" in call_args
        assert "[success]" in call_args
    
    def test_logger_warning(self, mocker):
        """测试 warning 方法"""
        from nexus_vpn.utils.logger import Logger, console
        mock_print = mocker.patch.object(console, 'print')
        Logger.warning("警告信息")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "警告信息" in call_args
        assert "[warning]" in call_args
    
    def test_logger_error(self, mocker):
        """测试 error 方法"""
        from nexus_vpn.utils.logger import Logger, console
        mock_print = mocker.patch.object(console, 'print')
        Logger.error("错误信息")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "错误信息" in call_args
        assert "[error]" in call_args
    
    def test_logger_run_cmd(self, mocker):
        """测试 run_cmd 方法"""
        from nexus_vpn.utils.logger import Logger, console
        mock_print = mocker.patch.object(console, 'print')
        Logger.run_cmd("apt-get update")
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "apt-get update" in call_args
        assert "[cmd]" in call_args
    
    def test_log_instance(self):
        """测试 log 实例是 Logger 类型"""
        from nexus_vpn.utils.logger import Logger, log
        assert isinstance(log, Logger)  # log 是 Logger 的实例
