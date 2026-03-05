package vrchat.FantasyNetwork;

import javax.swing.*;

public class Main {
    public static void main(String[] args) {
        System.out.println("VRChat 自动钓鱼系统启动中...");
        System.out.println("正在初始化窗口捕获...");

        SwingUtilities.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
            } catch (Exception e) {
                e.printStackTrace();
            }

            vrchat.FantasyNetwork.StreamViewer viewer = new vrchat.FantasyNetwork.StreamViewer();
            viewer.setVisible(true);

            System.out.println("系统启动完成！");
        });
    }
}