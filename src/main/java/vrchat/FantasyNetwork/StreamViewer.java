package vrchat.FantasyNetwork;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.image.BufferedImage;

public class StreamViewer extends JFrame {
    private JLabel statusLabel;
    private JLabel imageLabel;
    private JLabel infoLabel;
    private JButton startButton;
    private JButton stopButton;
    private JTextField windowTitleField;
    private volatile boolean capturing = false;
    private WindowCapture windowCapture;

    public StreamViewer() {
        setTitle("VRChat自动钓鱼 - 窗口捕获");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setSize(900, 700);
        setLocationRelativeTo(null);
        setLayout(new BorderLayout(10, 10));

        initComponents();

        windowCapture = new WindowCapture();
        
        addWindowListener(new java.awt.event.WindowAdapter() {
            @Override
            public void windowClosing(java.awt.event.WindowEvent e) {
                stopCapture();
            }
        });
    }

    private void initComponents() {
        JPanel topPanel = new JPanel(new BorderLayout(10, 10));
        topPanel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

        statusLabel = new JLabel("状态: 未捕获");
        statusLabel.setFont(new Font("Microsoft YaHei", Font.PLAIN, 14));
        topPanel.add(statusLabel, BorderLayout.WEST);

        JPanel controlPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT, 10, 0));

        JLabel windowLabel = new JLabel("窗口标题:");
        windowLabel.setFont(new Font("Microsoft YaHei", Font.PLAIN, 12));
        controlPanel.add(windowLabel);

        windowTitleField = new JTextField("VRChat", 15);
        windowTitleField.setFont(new Font("Microsoft YaHei", Font.PLAIN, 12));
        controlPanel.add(windowTitleField);

        startButton = new JButton("开始捕获");
        startButton.setFont(new Font("Microsoft YaHei", Font.PLAIN, 12));
        startButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                startCapture();
            }
        });

        stopButton = new JButton("停止捕获");
        stopButton.setFont(new Font("Microsoft YaHei", Font.PLAIN, 12));
        stopButton.setEnabled(false);
        stopButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                stopCapture();
            }
        });

        controlPanel.add(startButton);
        controlPanel.add(stopButton);
        topPanel.add(controlPanel, BorderLayout.EAST);

        add(topPanel, BorderLayout.NORTH);

        JPanel centerPanel = new JPanel(new BorderLayout());
        centerPanel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

        imageLabel = new JLabel("等待捕获...", SwingConstants.CENTER);
        imageLabel.setBackground(Color.DARK_GRAY);
        imageLabel.setOpaque(true);
        imageLabel.setForeground(Color.WHITE);
        imageLabel.setFont(new Font("Microsoft YaHei", Font.BOLD, 16));
        imageLabel.setPreferredSize(new Dimension(640, 480));

        JScrollPane scrollPane = new JScrollPane(imageLabel);
        scrollPane.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);
        scrollPane.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED);
        centerPanel.add(scrollPane, BorderLayout.CENTER);

        add(centerPanel, BorderLayout.CENTER);

        JPanel infoPanel = new JPanel(new BorderLayout(10, 10));
        infoPanel.setBorder(BorderFactory.createEmptyBorder(0, 10, 10, 10));

        infoLabel = new JLabel("<html>提示: 输入窗口标题（如：VRChat）点击开始捕获</html>");
        infoLabel.setFont(new Font("Microsoft YaHei", Font.PLAIN, 11));

        infoPanel.add(infoLabel, BorderLayout.WEST);

        add(infoPanel, BorderLayout.SOUTH);
    }

    private void startCapture() {
        if (capturing) {
            return;
        }

        String windowTitle = windowTitleField.getText().trim();
        if (windowTitle.isEmpty()) {
            JOptionPane.showMessageDialog(this, "请输入窗口标题", "错误", JOptionPane.ERROR_MESSAGE);
            return;
        }

        capturing = true;
        statusLabel.setText("状态: 捕获中");
        statusLabel.setForeground(new Color(0, 150, 0));
        startButton.setEnabled(false);
        stopButton.setEnabled(true);
        windowTitleField.setEnabled(false);
        imageLabel.setText("捕获中...");
        imageLabel.setForeground(Color.GREEN);

        windowCapture.setWindowTitle(windowTitle);
        windowCapture.setFrameCallback(this::displayFrame);
        windowCapture.start();

        infoLabel.setText("<html>正在捕获窗口: " + windowTitle + "</html>");
    }

    private void displayFrame(BufferedImage frame) {
        if (!capturing) {
            return;
        }

        SwingUtilities.invokeLater(() -> {
            ImageIcon icon = new ImageIcon(frame);
            imageLabel.setText("");
            imageLabel.setIcon(icon);
            
            Rectangle bounds = windowCapture.getWindowBounds();
            if (bounds != null) {
                infoLabel.setText("<html>正在捕获窗口: " + windowTitleField.getText() + 
                    " | 分辨率: " + bounds.width + "x" + bounds.height + "</html>");
            }
        });
    }

    private void stopCapture() {
        if (!capturing) {
            return;
        }

        capturing = false;
        statusLabel.setText("状态: 已停止");
        statusLabel.setForeground(Color.RED);
        startButton.setEnabled(true);
        stopButton.setEnabled(false);
        windowTitleField.setEnabled(true);
        imageLabel.setText("已停止捕获");
        imageLabel.setForeground(Color.WHITE);
        imageLabel.setIcon(null);

        windowCapture.stop();
        infoLabel.setText("<html>提示: 输入窗口标题（如：VRChat）点击开始捕获</html>");
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
            } catch (Exception e) {
                e.printStackTrace();
            }

            StreamViewer viewer = new StreamViewer();
            viewer.setVisible(true);
        });
    }
}