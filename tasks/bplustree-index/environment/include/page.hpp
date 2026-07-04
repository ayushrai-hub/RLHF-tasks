#ifndef BPT_PAGE_HPP
#define BPT_PAGE_HPP

#include <cstdint>
#include <cstddef>

namespace bpt {

static const std::size_t PAGE_SIZE = 4096;
static const std::size_t LEAF_CAP = 4;
static const std::size_t INT_FANOUT = 5;
static const std::uint32_t NO_PAGE = 0xFFFFFFFFu;

static const std::uint32_t SB_PAGE_SIZE = 4096;

void put_u16(unsigned char* p, std::uint16_t v);
void put_u32(unsigned char* p, std::uint32_t v);
void put_u64(unsigned char* p, std::uint64_t v);

std::uint16_t get_u16(const unsigned char* p);
std::uint32_t get_u32(const unsigned char* p);
std::uint64_t get_u64(const unsigned char* p);

}

#endif
