//==========================================================================
//  本文件由《芯片验证日记》整理分享，仅供学习交流使用。
//--------------------------------------------------------------------------
//  公众号 / 视频号：芯片验证日记
//  知识星球：7833526 —— 一年 365 天答疑，为您的工作和学习保驾护航！
//
//  已成功指导 200+ 位芯片同行求职上岸，收获满意 Offer；
//  提供求职套餐、职业规划等服务，欢迎咨询微信：DV365-DV_Daily。
//==========================================================================

// Self-contained testbench for the wave-mcp quickstart.
//
// The --trace-fst flag makes $dumpfile/$dumpvars write a real FST directly, so
// this needs NO commercial simulator (xrun) and NO vcd2fst. Build with
// `verilator --binary --trace-fst` and run the produced binary; it drops
// `counter.fst` in the current directory.
module top_tb;
    logic       clk = 1'b0;
    logic       rst_n;
    logic [7:0] count;
    logic       overflow;

    counter u_counter (
        .clk      (clk),
        .rst_n    (rst_n),
        .count    (count),
        .overflow (overflow)
    );

    // 10 time-unit clock period
    always #5 clk = ~clk;

    initial begin
        $dumpfile("counter.fst");
        $dumpvars(0, top_tb);

        rst_n = 1'b0;
        #12 rst_n = 1'b1;   // release reset after a couple of edges
        #600;               // ~60 clocks of counting
        $finish;
    end
endmodule
