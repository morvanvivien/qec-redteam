// Exercises the OSD combination sweep with k non-pivot columns and a given order.
//
//   test_combination_sweep <dense|sparse> K ORDER DECODES
//
// Prints one line per decode (the decoded bit string) so that two builds can be
// compared byte for byte. Built against libc++ with hardening, any out-of-bounds
// std::vector::operator[] traps immediately, whatever the allocator.

#include <cstdio>
#include <cstdlib>
#include <random>
#include <string>
#include <vector>

#include "osd_dense.hpp"

namespace {

// m x (m + k) matrix of rank m whose k non-pivot columns all come before the
// rank is full: e_0 .. e_{m-2}, then k random combinations of those rows, then
// e_{m-1}. PluDecomposition::rref stops at full rank, so the order matters.
std::vector<std::vector<int>> make_columns(int m, int k, std::mt19937 &rng) {
    std::vector<std::vector<int>> columns;
    for (int r = 0; r < m - 1; r++) columns.push_back({r});
    std::bernoulli_distribution coin(0.3);
    for (int c = 0; c < k; c++) {
        std::vector<int> rows;
        for (int r = 0; r < m - 1; r++) if (coin(rng)) rows.push_back(r);
        if (rows.empty()) rows.push_back(c % (m - 1));
        columns.push_back(rows);
    }
    columns.push_back({m - 1});
    return columns;
}

std::vector<uint8_t> random_syndrome(const std::vector<std::vector<int>> &columns, int m, std::mt19937 &rng) {
    std::vector<uint8_t> syndrome(m, 0);
    std::bernoulli_distribution flip(0.08);
    for (const auto &column: columns)
        if (flip(rng))
            for (int r: column) syndrome[r] ^= 1;
    return syndrome;
}

void print_bits(const std::vector<uint8_t> &bits) {
    std::string line;
    for (auto b: bits) line.push_back(b ? '1' : '0');
    std::puts(line.c_str());
}

int run_dense(int k, int order, int decodes) {
    const int m = 24, n = m + k;
    std::mt19937 rng(1234 + k);
    auto columns = make_columns(m, k, rng);
    auto plu = ldpc::gf2dense::PluDecomposition(m, n, columns);
    plu.rref();
    if (static_cast<int>(plu.not_pivot_cols.size()) != k) {
        std::fprintf(stderr, "unexpected dimension %zu\n", plu.not_pivot_cols.size());
        return 2;
    }
    std::vector<double> weights(n, 1.0);
    auto decoder = ldpc::osd::DenseOsdDecoder(columns, plu, ldpc::osd::COMBINATION_SWEEP, order, n, m, weights);
    for (int i = 0; i < decodes; i++) {
        auto syndrome = random_syndrome(columns, m, rng);
        print_bits(decoder.osd_decode(syndrome));
    }
    return 0;
}

int run_sparse(int k, int order, int decodes) {
    const int m = 24, n = m + k;
    std::mt19937 rng(4321 + k);
    auto columns = make_columns(m, k, rng);
    ldpc::bp::BpSparse pcm(m, n);
    for (int c = 0; c < n; c++)
        for (int r: columns[c]) pcm.insert_entry(r, c);
    std::vector<double> channel(n, 0.05);
    auto decoder = ldpc::osd::OsdDecoder(pcm, ldpc::osd::COMBINATION_SWEEP, order, channel);
    std::uniform_real_distribution<double> llr(-2.0, 4.0);
    for (int i = 0; i < decodes; i++) {
        auto syndrome = random_syndrome(columns, m, rng);
        std::vector<double> log_prob_ratios(n);
        for (auto &x: log_prob_ratios) x = llr(rng);
        print_bits(decoder.decode(syndrome, log_prob_ratios));
    }
    return 0;
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 5) {
        std::fprintf(stderr, "usage: %s <dense|sparse> K ORDER DECODES\n", argv[0]);
        return 2;
    }
    const std::string which = argv[1];
    const int k = std::atoi(argv[2]), order = std::atoi(argv[3]), decodes = std::atoi(argv[4]);
    return which == "dense" ? run_dense(k, order, decodes) : run_sparse(k, order, decodes);
}
